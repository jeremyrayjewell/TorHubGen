# TorHubGen (Temporary Onion Communication Hub Generator)

This repository currently contains **no code**.

It contains a **pre-implementation threat model** for a proposed tool named **TorHubGen**. The threat model exists to define strict scope limits, reject unsafe assumptions, and reduce the risk of false confidence in any future implementation.

## Status

- **Stage:** Threat model only (no implementation)
- **Build/use:** Not possible (no generator exists yet)
- **Roadmap:** Not promised. The threat model explicitly allows for the possibility that this project should **not** ship.

## What this project is (proposed)

TorHubGen is intended to be a **generator**, not a hosted service.

If implemented, TorHubGen would generate a temporary, local configuration bundle to help small, trusted groups create **short-lived Tor onion services** with conservative defaults and explicit teardown guidance.

The core problem it targets is **setup risk** (avoidable operational mistakes), not communication or anonymity.

## What this project is not

TorHubGen is **not**:

- a messaging app
- a hosting platform
- a “secure chat” product
- an anonymity guarantee

The threat model explicitly states what TorHubGen does **not** protect against, including (non-exhaustive):

- compromised devices
- insider betrayal
- traffic analysis/correlation
- identification through user behavior
- legal or physical harm

## Read the threat model first

**Do not treat this repository as a tool.**  
If you are evaluating this project, start here:

- `threat-model.md`

That document defines:

- the exact problem scope
- explicit non-goals
- attacker models
- acceptable vs unacceptable risks
- minimum viable design constraints
- expected failure modes
- mandatory safety language

Any future code that contradicts the threat model should be treated as **incorrect by definition**.

## Contributions

Contributions are not currently solicited.

If this project progresses, contributions (if accepted) will be evaluated primarily against the constraints in `threat-model.md`. Features that expand scope, increase user confidence without real protection, or reduce clarity in the name of convenience will be rejected.

## Non-endorsement

The existence of this repository and threat model **does not imply** that using Tor, onion services, or any future TorHubGen implementation is advisable in any particular situation.

If you are under real risk, seek qualified, context-specific guidance. A generic generator cannot evaluate your threat environment.

## License

License not yet selected. 
