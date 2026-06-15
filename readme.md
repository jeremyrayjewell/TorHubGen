# TorHubGen

TorHubGen is an early-stage Python project for running a short-lived Tor onion service in a more controlled, testable way.

The current implementation launches a private Tor instance, creates one ephemeral v3 onion service, exposes a minimal localhost-only bulletin-board HTTP surface, enforces a required lifetime, and tears the appliance down loudly when the run ends or something fails.

This repository is intentionally narrow. It is about lifecycle correctness, explicit teardown, and safer operational defaults, not about adding a full forum platform or making security guarantees.

## What Problem It Solves

TorHubGen is aimed at a specific operational problem:

- temporary Tor hidden-service experiments are easy to misconfigure
- teardown is often treated as an afterthought
- persistent state and silent failures can outlive the intended session
- security-sensitive behavior is easy to oversell or leave implicit

TorHubGen tries to reduce those mistakes by keeping the design small and auditable:

- explicit runtime lifetime is mandatory
- the local web service binds only to `127.0.0.1`
- the onion service is ephemeral and created with `ADD_ONION NEW:ED25519-V3 Flags=DiscardPK`
- cleanup is attempted automatically and failures are surfaced instead of hidden

## Current Status

- **Stage:** threat model complete, early implementation in progress
- **Current focus:** proving lifecycle guarantees and testability
- **Recent validation:** local real-Tor runs and a limited Fly.io onion deployment test have completed successfully
- **Real-world use:** not recommended
- **Authority:** [docs/threat-model.md](docs/threat-model.md) is the project's constraining document

Current implementation is intentionally limited to:

- one private Tor process
- one ephemeral v3 onion service
- one minimal in-memory bulletin board
- `GET /` for a minimal browser UI
- `GET /messages`
- `POST /message` with JSON: required `"content"` string and optional `"pseudonym"` string
- explicit shutdown and teardown behavior

## What TorHubGen Does Today

From the current codebase, TorHubGen:

- launches Tor with an isolated temporary `DataDirectory`
- opens a localhost-only ControlPort with Tor cookie auth enabled
- requires explicit SAFECOOKIE control authentication before proceeding
- starts a small localhost-only HTTP server
- serves a minimal browser UI at `GET /`
- maps that server to a single ephemeral onion service
- keeps message data in memory only
- enforces a maximum runtime of 1 hour
- shuts down if Tor exits unexpectedly
- attempts teardown of the onion service, web server, in-memory state, Tor process, and temp directory

## What It Does Not Do

TorHubGen is **not**:

- a production-ready hosting tool
- a persistent forum or messaging platform
- a file-sharing tool
- a clearnet/Tor hybrid deployment utility
- an anonymity, confidentiality, or legal-protection guarantee
- a project suitable for high-risk situations by default

It does **not** solve:

- endpoint compromise
- participant leaks
- traffic analysis or correlation
- copied or redistributed content
- real-world legal or physical risk

## Requirements

Runtime requirements:

- Python 3.10+  
  The code uses modern type syntax and has been exercised in a Python 3.13 environment.
- A Tor binary available on `PATH`, or an explicit path passed via `--tor-cmd`
- The Python `stem` library for Tor control-port interactions

Development and test requirements:

- `pytest` for the test suite

## Basic Setup

Example setup from the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install stem pytest
```

If Tor is not on `PATH`, keep its executable path available for `--tor-cmd`.

## Basic Usage

Run the built-in preflight checks:

```powershell
python -m torhubgen selfcheck
```

Start a short-lived appliance run:

```powershell
python -m torhubgen --lifetime-seconds 300
```

Use an explicit Tor executable if needed:

```powershell
python -m torhubgen --lifetime-seconds 300 --tor-cmd C:\path\to\tor.exe
```

The older entrypoint still works as a compatibility shim:

```powershell
python atomic_wrapper.py --lifetime-seconds 300
```

Current web/API surface:

- `GET /` serves a minimal browser UI for viewing and posting messages
- `GET /messages` returns the current in-memory message list as JSON
- `POST /message` expects JSON with a required `"content"` string and an optional `"pseudonym"` string

## Limited Fly.io Onion Deployment Test

This repository now includes a minimal `Dockerfile`, `.dockerignore`, and `fly.toml` draft for an experimental Fly.io deployment path. A limited onion-only Fly.io deployment test has passed, but this remains a narrow, early-stage deployment path rather than a general hosting recommendation.

Important constraints for this deployment model:

- keep TorHubGen's local HTTP server bound to `127.0.0.1`
- do **not** add a public Fly `[http_service]` or `[[services]]` block
- access the app only through the ephemeral `.onion` address printed in logs
- every run gets a new ephemeral onion address
- messages remain in memory only and disappear when the process ends

Example Fly workflow:

```powershell
fly launch --no-deploy
fly deploy
fly logs -a <app-name>
```

Before deploying, replace the placeholder app name in `fly.toml` with your own Fly app name. Do not expose the local HTTP port as a public Fly service for this project.

## Screenshots / Milestones

### Local TorHubGen Browser UI

![Placeholder screenshot for the local TorHubGen browser UI](docs/assets/screenshots/local-ui-placeholder.png)

Future screenshot: the localhost-served bulletin board UI showing current in-memory messages and the minimal post form.

### Tor Bootstrap, SAFECOOKIE, and Onion Creation Logs

![Placeholder screenshot for successful Tor bootstrap and onion creation logs](docs/assets/screenshots/local-onion-startup-placeholder.png)

Future screenshot: console output showing Tor bootstrap, explicit SAFECOOKIE authentication, and the ephemeral `.onion` address creation message.

### Fly.io Onion Deployment Visible in Tor Browser

![Placeholder screenshot for the Fly.io onion deployment UI](docs/assets/screenshots/fly-onion-ui-placeholder.png)

Future screenshot: the deployed TorHubGen board reached through Tor Browser using the ephemeral Fly-hosted `.onion` address.

### Clean Teardown After Lifetime Expiry

![Placeholder screenshot for teardown after lifetime expiry](docs/assets/screenshots/teardown-placeholder.png)

Future screenshot: logs showing lifetime expiry, shutdown request handling, cleanup steps, and a non-restarting end state.

## SAFECOOKIE Security Note

Tor's ControlPort is a privileged interface. TorHubGen does **not** use unauthenticated control connections, password auth, or a silent fallback to legacy `COOKIE` authentication.

Instead, it explicitly requires `SAFECOOKIE`, which is Tor's challenge-response method built around a local authentication cookie. At startup, TorHubGen:

- queries Tor for supported control-port auth methods
- verifies that `SAFECOOKIE` is offered
- uses Stem's SAFECOOKIE flow directly
- fails closed if SAFECOOKIE is unavailable or the auth exchange fails

This matters because the project is trying to make security-sensitive control behavior explicit instead of relying on looser defaults.

## Running Tests

Run the main test suite:

```powershell
python -m pytest -q
```

Run the opt-in real Tor integration test:

```powershell
$env:TORHUBGEN_RUN_TOR_INTEGRATION='1'
python -m pytest -q tests\test_real_tor_integration.py
```

The integration test requires:

- a real Tor binary available on `PATH`
- `stem` installed

## Repository Highlights

- [torhubgen/tor_controller.py](torhubgen/tor_controller.py): Tor process launch, SAFECOOKIE authentication, and onion-service creation
- [torhubgen/lifecycle.py](torhubgen/lifecycle.py): runtime orchestration, lifetime enforcement, signal handling, and fail-closed shutdown behavior
- [torhubgen/board_server.py](torhubgen/board_server.py): localhost-only in-memory HTTP surface with bounded request handling and simple rate limiting
- [torhubgen/teardown.py](torhubgen/teardown.py): explicit teardown reporting for each cleanup step
- [tests/](tests/): unit tests with fakes and mocks plus an opt-in real Tor integration test

## Skills This Project Demonstrates

This repo is a good snapshot of the kinds of work relevant to IT Support, Technical Support, and security-adjacent engineering roles:

- Python troubleshooting and maintainable CLI code
- service lifecycle management and teardown handling
- reading and enforcing documented requirements
- defensive authentication behavior and fail-closed thinking
- localhost-only service hardening
- structured testing with unit and integration coverage
- debugging and documenting environment-dependent issues
- writing clear operator-facing error messages and technical documentation

## Read the Threat Model First

This repository should be interpreted through its design constraints, not as a finished product. Start with:

- [docs/threat-model.md](docs/threat-model.md)
- [docs/development_process.md](docs/development_process.md)

If code and documentation disagree with the threat model, the threat model wins.

## License

License not yet selected. No guarantees are made regarding future availability or support.

## Author

Jeremy Ray Jewell  
[GitHub](https://github.com/jeremyrayjewell) | [LinkedIn](https://www.linkedin.com/in/jeremyrayjewell)
