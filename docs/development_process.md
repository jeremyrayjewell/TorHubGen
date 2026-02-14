# TorHubGen Development Process

This document defines the development ordering, invariants, validation requirements, and stop-ship conditions for TorHubGen. It is binding for implementation decisions and must be reviewed alongside [`threat-model.md`](./threat-model.md).

---

## 1. Development Ordering

TorHubGen development proceeds strictly from **control-plane correctness** to **application functionality**.

No forum, messaging, or user-facing features may be implemented until the atomic lifecycle properties defined in [`threat-model.md`](./threat-model.md) are:

- Demonstrated
- Empirically validated
- Fail-closed under negative conditions

The initial development focus is the appliance wrapper responsible for:

- Process-level ephemerality
- Enforced lifetime
- Deterministic teardown
- Explicit failure visibility

---

## 2. Phase 1 — Atomic Process

### 2.1 Scope

Phase 1 concerns only control-plane behavior.  
No application-layer features are in scope.

Phase 1 is complete when the following invariants are demonstrated:

- A private Tor instance launches with isolated state
- A V3 ephemeral onion service is created without writing private keys to disk
- A mandatory, bounded lifetime is enforced
- Teardown occurs on:
  - Timer expiry
  - Operator signal
  - Unexpected crash
- Teardown failures are explicitly surfaced
- Unexpected Tor termination causes immediate shutdown (no silent continuation)

---

### 2.2 Demonstration and Validation Status

Phase 1 has been demonstrated on a host operating system without containers, sandboxes, or service managers. This ensures lifecycle and teardown behavior are directly observable and not abstracted by external tooling.

The following behaviors were empirically validated:

#### Control-Plane Properties

- Tor launches with an isolated temporary `DataDirectory`
- Onion service created via:
```
ADD_ONION NEW:ED25519-V3 Flags=DiscardPK
```
- No onion private keys written to disk
- ControlPort authentication is local-only and cookie-based
- No application-layer service outlives the Tor process

#### Lifecycle Enforcement

- Mandatory lifetime enforced via monotonic timer
- Shutdown on lifetime expiry
- Shutdown on operator interrupt (SIGINT)
- Immediate shutdown on unexpected Tor process termination
- Misconfiguration results in fail-closed behavior

#### Teardown Semantics

- Teardown executes via a mandatory `finally` path
- Teardown distinguishes between:
- Expected control-channel unavailability (Tor already exited)
- True cleanup failures
- True cleanup failures are emitted as fatal conditions
- No silent suppression of cleanup errors

---

### 2.3 Stop-Ship Conditions (Phase 1)

The following conditions invalidate Phase 1 and block further development:

- Silent continuation after Tor process death
- Onion key material written to persistent storage
- Failure to enforce mandatory lifetime
- Teardown failures not explicitly surfaced
- Orphaned processes remaining after shutdown

Phase 1 is considered complete only if none of these conditions occur under negative testing.

---

## 3. Packaging and Deployment Constraints

For Phase 1:

- Container-based or sandboxed packaging mechanisms (e.g., Docker, Snap) are out of scope.
- Validation must occur on a host OS without lifecycle abstraction layers.
- No service manager may supervise or restart the process during validation.

This constraint ensures atomic process behavior is intrinsic, not delegated.

---

## 4. Change Control

Any change that weakens:

- Lifecycle guarantees
- Teardown visibility
- Fail-closed behavior
- Safety messaging
- Isolation properties

requires revisiting both:

- `development_process.md`
- `threat-model.md`

before implementation proceeds.

Control-plane guarantees take precedence over feature development.

---

## 5. Phase 1 Status

Phase 1 control-plane invariants have been validated and are considered complete.

Application-layer development may proceed only insofar as it preserves these established lifecycle guarantees.
