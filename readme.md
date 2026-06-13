# TorHubGen

TorHubGen is a **self-deploying, ephemeral, Tor-only bulletin board appliance**.

This repository documents and implements a narrowly scoped project whose primary goal is to reduce **operational and lifecycle mistakes** when hosting short-lived, forum-style communications over Tor. The project is intentionally conservative, threat-model–driven, and designed to avoid creating false confidence.

TorHubGen is **not** a platform, not a hosted service, and not a promise of safety or anonymity.

---

## Status

- **Stage:** Threat model complete; early implementation in progress  
- **Build/use:** Not yet recommended for real-world use  
- **Current engineering goal:** prove and test core lifecycle properties for a narrow Alpha 0.1  
- **Roadmap:** Not promised  
- **Authority:** `docs/threat-model.md` is authoritative and constraining  

The threat model explicitly allows for the possibility that this project should **not ship** if implementation cannot meet its safety and scope constraints.

Current implementation work is focused on:

- explicit lifetime enforcement
- localhost-only binding
- ephemeral onion creation
- loud, testable teardown behavior

This repository still does **not** make anonymity, safety, confidentiality, or legal-protection claims.

Current CLI entry points from the repository root:

- `python -m torhubgen --lifetime-seconds 300`
- `python -m torhubgen selfcheck`
- `python atomic_wrapper.py --lifetime-seconds 300`  
  Compatibility path for the previous single-file entrypoint.

Tor control authentication is enforced as `SAFECOOKIE`-only. TorHubGen queries
Tor's advertised control-port auth methods and fails closed if `SAFECOOKIE` is
not offered or cannot be completed successfully. It does not fall back to
legacy `COOKIE` authentication.

---

## What this project is

TorHubGen is designed to:

- Launch a local **Tor onion service**
- Host a **minimal, forum-style bulletin board**
- Run for a **fixed, declared lifetime**
- Attempt **automatic teardown and data removal** on expiration or termination
- Make failure to tear down **visible and explicit**

The bulletin board supports:
- Public threaded posts
- Optional, **ephemeral private messages** between active participants  
  (temporary, session-scoped, disabled by default)

All functionality exists **only for the lifetime of the running instance**.

---

## What this project is not

TorHubGen is **not**:

- a persistent forum or community platform
- a messaging or chat application
- a file-sharing or file-transfer service
- a hosting provider
- a general-purpose Tor deployment tool
- a safety, anonymity, or confidentiality guarantee
- suitable for high-risk environments by default

It does **not** protect against:

- compromised devices
- malicious or dishonest participants
- traffic analysis or correlation
- copying, recording, or redistribution of content
- legal or physical harm

---

## Design philosophy

TorHubGen is built around the following principles:

- **Ephemerality is enforced**, not optional  
- **Teardown is a first-class concern**, not an afterthought  
- **Mistake prevention outweighs convenience**  
- **Scope creep is treated as a security regression**  
- **False confidence is considered a primary hazard**

The project intentionally limits features, adds friction at dangerous points, and rejects designs that imply protection it cannot provide.

---

## Private messaging (clarification)

TorHubGen may optionally support **temporary private messages**:

- Messages exist only while the board is running
- No inboxes, archives, or offline delivery
- No delivery guarantees
- No confidentiality guarantees
- Messages may be copied or recorded by recipients
- Automatically disabled when the board expires

Private messaging does **not** make communication safer than public posting.

---

## External links and file sharing

TorHubGen does **not** manage or host files.

Users may choose to share **external links** (for example, OnionShare links) within posts or private messages. Such links are treated as opaque text.

TorHubGen:
- does not verify, preview, or manage external links
- does not coordinate lifecycles with external tools
- does not vouch for the safety of linked content

Files shared via external links may be malicious. Users must assess risk independently.

---

## Read the threat model first

**Do not treat this repository as a finished tool.**

Start with:

- `docs/threat-model.md`

That document defines:

- the exact problem scope
- explicit non-goals
- attacker models
- acceptable vs unacceptable risks
- design constraints
- expected failure modes
- mandatory safety language

Any code or feature that contradicts the threat model should be treated as **incorrect by definition**.

---

## Contributions

Contributions are not currently solicited.

If this project progresses, contributions (if accepted) will be evaluated **primarily against the threat model**, not feature requests or usability goals. Features that expand scope, introduce persistence, or increase user confidence without real protection will be rejected.

---

## Non-endorsement

The existence of this project does **not** imply that using Tor, onion services, or TorHubGen is advisable in any particular situation.

TorHubGen cannot evaluate your threat environment.  
If you are under real risk, seek qualified, context-specific guidance.

---

## License

License not yet selected.  
No guarantees are made regarding future availability or support.

---

## Author

Jeremy Ray Jewell  
[GitHub](https://github.com/jeremyrayjewell) · [LinkedIn](https://www.linkedin.com/in/jeremyrayjewell)
