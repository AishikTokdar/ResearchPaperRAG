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
from packaging.version import Version


def profile_requirements(path: Path) -> list[Requirement]:
    result = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-r "):
            result.extend(profile_requirements(path.parent / line[3:].strip()))
        else:
            result.append(Requirement(line))
    return result


def installed_profile(profile: str = "api") -> dict[str, str]:
    config = Path(sys.prefix) / "pyvenv.cfg"
    if config.is_file() and any(
        line.replace(" ", "").casefold() == "include-system-site-packages=true"
        for line in config.read_text(encoding="utf-8").splitlines()
    ):
        raise SystemExit("Use an isolated virtual environment without system site packages")
    filename = "requirements.txt" if profile == "full" else "requirements-api.txt"
    requirements = Path(__file__).resolve().parents[1] / "backend" / filename
    queue = deque(profile_requirements(requirements))
    # HTTP clients may auto-enable these even without declaring a Brotli extra.
    for optional in ("brotli", "brotlicffi"):
        try:
            distribution(optional)
        except PackageNotFoundError:
            continue
        queue.append(Requirement(optional))
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
        # PyPI advisories use the upstream release, not the CPU wheel suffix.
        pins[name] = Version(package.version).public
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
    parser.add_argument("--profile", choices=("api", "full"), default="api")
    args = parser.parse_args()
    pins = installed_profile(args.profile)
    print(f"Auditing {len(pins)} installed {args.profile}-profile packages", flush=True)
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
        raise SystemExit(subprocess.run(command, check=False).returncode)
