This document defines the development ordering, invariants, and stop-ship conditions for TorHubGen. It is binding for implementation decisions and must be reviewed alongside [`threat-model.md`](./threat-model.md).

# Purpose and Development Ordering

TorHubGen development proceeds from control-plane correctness to application functionality.

No forum, messaging, or user-facing features may be implemented until the atomic lifecycle properties defined in [`threat-model.md`](./threat-model.md) are demonstrated and testable. The initial development focus is the appliance wrapper responsible for process-level ephemerality, enforced lifetime, and teardown.

## Phase 1 Scope (Atomic Process)
Phase 1 is complete when the following properties are demonstrated:
- A private Tor instance can be launched with isolated state
- A V3 ephemeral onion service is created without writing private keys to disk
- A mandatory lifetime is enforced
- Teardown occurs on timer expiry, signal, or crash
- Any failure to teardown is made explicitly visible
- Unexpected Tor process termination causes immediate shutdown rather than silent continuation

No application-layer features are in scope for Phase 1.

### Phase 1 Demonstration Status

Phase 1 has been **demonstrated on a host OS** and is considered complete.

The following properties were empirically observed during execution:

- Tor launches as a private instance with an isolated temporary `DataDirectory`
- A V3 onion service is created via `ADD_ONION NEW:ED25519-V3 Flags=DiscardPK`
- No onion private keys are written to disk
- A mandatory lifetime is enforced via a monotonic timer
- Shutdown occurs on lifetime expiry
- Teardown is executed via a mandatory `finally` path
- Teardown failures are emitted loudly
- ControlPort authentication is local-only and cookie-based
- No application-layer services outlive the Tor process
- Unexpected Tor process termination results in immediate shutdown

Phase 1 was validated without containers, sandboxes, or service managers,
ensuring that process lifetime and teardown behavior are directly observable.

This milestone establishes the control-plane invariants required before
any application-layer functionality may be introduced.


### Packaging and Deployment Constraints (Phase 1)

Container-based or sandboxed packaging mechanisms (including Docker and Snap) are out of scope for Phase 1.

The atomic-process milestone must be validated on a host OS without packaging abstractions that may obscure process lifecycle, persistence, or teardown behavior.

# Change Control

Any change that weakens lifecycle guarantees, teardown visibility, or safety messaging requires revisiting both this document and `threat-model.md` before implementation.