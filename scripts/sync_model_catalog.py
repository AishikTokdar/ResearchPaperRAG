"""Copy the reviewed backend catalog into the standalone frontend build."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
source = root / "backend/app/model_catalog.json"
target = root / "frontend/src/lib/model-catalog.json"
target.write_bytes(source.read_bytes())
print("Frontend model catalog synchronized.")
