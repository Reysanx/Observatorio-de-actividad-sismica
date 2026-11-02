# Windows Toolchain Preparation

Windows setup for Python 3.11, Docker Desktop, and a reproducible Playwright CLI should use explicit version selection and per-shell activation.

## What Happened
For Observatorio de Actividad Sísmica task t7, `winget` supplied Python 3.11.9, while the initial `python` command resolved to the WindowsApps shim. `py -3.11` worked, and prepending the Python311 install directories made `python` resolve predictably. Docker CLI and Compose were installed, but the Docker Desktop daemon needed to be started before `docker info` succeeded. Playwright 1.64.1 and Chromium could be prepared via pinned `npx` commands without adding files to a project that had no frontend manifest yet.

## Takeaway
On Windows, verify the interpreter actually selected, not only that a runtime exists. Prefer `py -3.11` or give downstream agents the tested PATH activation snippet. For a not-yet-scaffolded frontend, pin the Playwright CLI in `npx` and install the browser cache; let the frontend task add its own local test dependency. Check `docker info` after starting Docker Desktop—`docker --version` alone does not establish daemon readiness.

## History
- 2026-11-02 (Observatorio-de-actividad-s-smica/t7): initial
