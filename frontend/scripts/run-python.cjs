// Runs a Python script with the backend's virtualenv (Windows or Unix layout).
const { spawnSync } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const venv = path.resolve(__dirname, "..", "..", ".venv");
const candidates = [path.join(venv, "Scripts", "python.exe"), path.join(venv, "bin", "python")];
const py = candidates.find((p) => fs.existsSync(p)) || "python";
const r = spawnSync(py, process.argv.slice(2), { stdio: "inherit", env: { ...process.env, PYTHONIOENCODING: "utf-8" } });
process.exit(r.status ?? 1);
