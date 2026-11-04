"""Audit the installed API dependency closure, excluding unrelated optional packages.

This is an installed-platform snapshot, not a dependency resolver or release lock.
"""

import argparse
import subprocess
import sys
import tempfile
from collections import deque
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def installed_profile() -> dict[str, str]:
    requirements = Path(__file__).resolve().parents[1] / "backend/requirements-api.txt"
    queue = deque(
        Requirement(line.strip())
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    )
    checked = set()
    pins = {}
    while queue:
        requirement = queue.popleft()
        name = canonicalize_name(requirement.name)
        extras = tuple(sorted(requirement.extras))
        if (name, extras) in checked:
            continue
        checked.add((name, extras))
        try:
            package = distribution(requirement.name)
        except PackageNotFoundError:
            raise SystemExit(f"Missing API dependency: {requirement.name}") from None
        if requirement.specifier and package.version not in requirement.specifier:
            raise SystemExit(
                f"Installed version is outside required range: {requirement.name}"
            )
        pins[name] = package.version
        for dependency in package.requires or []:
            child = Requirement(dependency)
            if child.marker is None or any(
                child.marker.evaluate({"extra": extra}) for extra in ("", *extras)
            ):
                queue.append(child)
    return pins


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Optional JSON audit report path")
    args = parser.parse_args()
    pins = installed_profile()
    print(f"Auditing {len(pins)} installed API-profile packages", flush=True)
    with tempfile.TemporaryDirectory(prefix="research-rag-audit-") as temporary:
        path = Path(temporary) / "requirements.txt"
        path.write_text(
            "\n".join(f"{name}=={version}" for name, version in sorted(pins.items()))
            + "\n",
            encoding="utf-8",
        )
        command = [
            sys.executable,
            "-B",
            "-m",
            "pip_audit",
            "--disable-pip",
            "--no-deps",
            "-r",
            str(path),
            "-f",
            "json",
        ]
        if args.output:
            command.extend(["-o", args.output])
        raise SystemExit(subprocess.run(command).returncode)
