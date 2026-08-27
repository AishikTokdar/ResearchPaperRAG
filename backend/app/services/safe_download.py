"""Size-bounded HTTP downloads pinned to a validated public IP (including redirects)."""

import http.client
import ipaddress
import socket
import time
from urllib.parse import urljoin, urlsplit


def public_addresses(host: str, port: int) -> list[str]:
    addresses = list(
        dict.fromkeys(
            str(row[4][0]) for row in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        )
    )
    if not addresses or any(not ipaddress.ip_address(ip).is_global for ip in addresses):
        raise ValueError("PDF URL must resolve exclusively to public addresses")
    return addresses


def download_pdf(url: str, max_bytes: int = 15 * 1024 * 1024) -> bytes:
    deadline = time.monotonic() + 20
    for _ in range(4):
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("Invalid PDF URL")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if port != (443 if parsed.scheme == "https" else 80):
            raise ValueError("Nonstandard PDF URL ports are not permitted")
        address = public_addresses(parsed.hostname, port)[0]
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("PDF download timed out")
        cls = (
            http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        )
        connection = cls(parsed.hostname, port, timeout=min(6, remaining))
        # Keep the hostname for TLS certificate verification and Host, but pin the socket
        # to the already-validated address so a second DNS lookup cannot rebind it.
        connection._create_connection = (  # type: ignore[attr-defined]
            lambda *args, _address=address, _port=port, _remaining=remaining, **kwargs: (
                socket.create_connection((_address, _port), timeout=min(6, _remaining))
            )
        )
        try:
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            connection.request(
                "GET",
                path,
                headers={"User-Agent": "ResearchPaperRAG/2.0", "Accept": "application/pdf"},
            )
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise ValueError("PDF redirect has no location")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError("PDF download was unsuccessful")
            length = response.getheader("Content-Length")
            if length and int(length) > max_bytes:
                raise ValueError("PDF exceeds download size limit")
            body = bytearray()
            while True:
                if time.monotonic() >= deadline:
                    raise TimeoutError("PDF download timed out")
                block = response.read(min(65536, max_bytes + 1 - len(body)))
                if not block:
                    break
                body.extend(block)
                if len(body) > max_bytes:
                    raise ValueError("PDF exceeds download size limit")
            if not body.startswith(b"%PDF-"):
                raise ValueError("Downloaded file is not a PDF")
            return bytes(body)
        finally:
            connection.close()
    raise ValueError("Too many PDF redirects")
