"""Prepare a clean, secret-free Gradio Space repository. Does not upload or deploy."""

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    backend = ROOT / "backend"
    shutil.copytree(backend / "app", output / "app", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in ("app.py", "gradio_app.py"):
        shutil.copy2(backend / name, output / name)
    shutil.copy2(backend / "requirements-api.txt", output / "requirements-api.txt")
    shutil.copy2(backend / "requirements.txt", output / "requirements.txt")
    shutil.copy2(backend / "requirements-gradio.txt", output / "requirements-gradio.txt")
    shutil.copy2(backend / "requirements-dev.txt", output / "requirements-dev.txt")
    (output / "backend").mkdir()
    shutil.copy2(backend / "README.md", output / "backend/README.md")
    for file in ROOT.glob("*.md"):
        shutil.copy2(file, output / ("PROJECT_README.md" if file.name == "README.md" else file.name))
    shutil.copytree(ROOT / "docs", output / "docs")
    readme = (backend / "README.md").read_text(encoding="utf-8").replace("](../", "](")
    (output / "README.md").write_text(readme, encoding="utf-8")
    print(f"Space files prepared: {output.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/huggingface")
    args = parser.parse_args()
    try:
        prepare(args.output)
    except FileExistsError:
        parser.error("Output already exists; choose a new empty output path.")
