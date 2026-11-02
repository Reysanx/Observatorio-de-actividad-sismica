# t7 — Local Toolchain Preparation

## Target Environment Preparation

**Status: READY**

### Preparation actions
- Installed Python using `winget install --exact --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements`; the package hash was verified by WinGet.
- Confirmed Node.js 22.15.0 and Docker Compose were already installed.
- Started Docker Desktop. The Docker daemon, initially unavailable, became reachable.
- Installed the pinned Playwright 1.64.1 Chromium browser binaries into the user cache using `npx`; no project `package.json` or source files were changed.

### Requested and installed versions
| Capability | Requested | Installed / verified |
|---|---|---|
| Python | 3.11 | 3.11.9 |
| Node.js | 22.15 | 22.15.0 |
| Docker Compose | Compose available | v5.6.1 |
| Docker Engine | Functional daemon | 29.9.2 |
| Playwright | Browser E2E available | CLI 1.64.1; Chromium and headless-shell build 1248 installed |

### Active defaults and command-resolution evidence
- Python's unmodified `python` command initially resolves to the WindowsApps shim. The requested interpreter is installed at `C:\Users\jasam\AppData\Local\Programs\Python\Python311\python.exe`.
- `py -3.11 --version` resolves to Python 3.11.9.
- After prepending the Python 3.11 install and Scripts directories to `PATH`, `Get-Command python` resolved to `Python311\python.exe`, `python --version` returned 3.11.9, and `python -m pip --version` returned pip 24.0 for Python 3.11.
- `Get-Command node` resolved to `C:\Program Files\nodejs\node.exe`; `node --version` returned v22.15.0.
- `Get-Command docker` resolved to Docker Desktop's CLI; `docker compose version` returned v5.6.1 and `docker info --format '{{.ServerVersion}}'` returned 29.9.2.
- `npx --yes playwright@1.64.1 --version` returned 1.64.1. `install --list` showed the Chromium and headless-shell browser caches.

### Versions planned commands will use
- `docker compose up --build -d` (from the repository root) will use Docker Compose v5.6.1 and Docker Engine 29.9.2. The project Compose file is not present yet; scaffold/startup is downstream work.
- Backend containers should continue to pin the planned `python:3.11-slim` image. The acceptance command specified by the project is `docker compose exec api pytest tests/test_acceptance.py -v`.
- Browser tests can invoke the prepared CLI with `npx --yes playwright@1.64.1 test` after the frontend test configuration and test files are added.

### Exact downstream activation commands (PowerShell)
Use the launcher to target Python 3.11 without changing the machine-wide default:
```powershell
py -3.11 --version
py -3.11 -m pip --version
```
Or activate Python 3.11 for the current shell:
```powershell
$env:Path = "$env:LOCALAPPDATA\Programs\Python\Python311;$env:LOCALAPPDATA\Programs\Python\Python311\Scripts;$env:Path"
python --version
```
Node, Compose, and the pinned browser tooling are available with:
```powershell
node --version
docker compose version
npx --yes playwright@1.64.1 --version
```
To reproduce the browser install if the user cache is cleared:
```powershell
npx --yes playwright@1.64.1 install chromium
```

### Missing tools, blockers, and downstream implications
- **Missing tools:** none for the requested host toolchain.
- **Blockers:** none for environment preparation. Docker Desktop is running and the daemon responds. The application cannot be started until the downstream Compose scaffold exists.
- The frontend/test package manifest does not exist yet, so Playwright is intentionally available through a version-pinned `npx` invocation and browser cache rather than a repo dependency. The frontend scaffold/test task should add a pinned project test dependency if its tests import `@playwright/test`.
- No credentials were used, and no Netlify or ngrok publication was attempted.

## Project Requirements Consulted
- `specs/001-observatorio-sismico/spec.md`
- `specs/001-observatorio-sismico/plan.md`
- `specs/001-observatorio-sismico/tasks.md`
- `specs/001-observatorio-sismico/data-spec.md`
- `specs/001-observatorio-sismico/acceptance-tests.md`
- `.specify/memory/constitution.md`
- `.agents/AGENTS.md`
- `.agents/subagents/01-platform-devops/AGENT.md`
- `.agents/rules/architecture_invariants.md`
- `.agents/rules/data_quality_rules.md`
- `.agents/skills/acceptance-testing/SKILL.md`
- `runtime-validation` skill and its Playwright reference

The workflow directory did not contain `context.md`, `decisions.md`, or a prior `team/devops` log/inbox. No dependency artifacts were assigned to t7.

## Upstream Artifacts Consumed
- none — no dependency artifacts provided

## Evidence Mapping
- none — no dependency artifacts provided

## Test Results
- **Passed:** 13 environment/setup checks
- **Failed:** 0
- **Skipped:** 0
- Python install: `winget install --exact --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements` — exit 0; Python 3.11.9 installed.
- Python resolution: `py -3.11 --version` and the documented PATH activation followed by `python --version` — both returned Python 3.11.9; pip reported 24.0.
- Node resolution: `node --version` — v22.15.0.
- Docker readiness: `docker compose version`, `docker info --format '{{.ServerVersion}}'`, and `docker compose ls --format json` — Compose v5.6.1, Engine 29.9.2, exit 0 (no Compose project is running yet).
- Browser install: `npx --yes playwright@1.64.1 install chromium` — exit 0; Chromium browser cache listed.
- Browser smoke: `npx --yes playwright@1.64.1 screenshot --browser chromium about:blank "$env:TEMP\playwright-smoke.png"` — exit 0; screenshot created (4,254 bytes) and removed after verification.
- No application build or application tests were run because the Compose application scaffold is a downstream task.
