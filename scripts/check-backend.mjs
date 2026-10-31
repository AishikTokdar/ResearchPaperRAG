import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const candidates = process.platform === "win32"
  ? [".venv/Scripts/python.exe", "backend/.venv/Scripts/python.exe"]
  : [".venv/bin/python", "backend/.venv/bin/python"];
const python = process.env.BACKEND_PYTHON || candidates.map(file => path.join(root, file)).find(existsSync) || "python";
const result = spawnSync(python, ["-B", path.join(root, "scripts/check_backend.py")], { stdio: "inherit", cwd: root });
if (result.error) console.error(result.error.message);
process.exitCode = result.status ?? 1;
