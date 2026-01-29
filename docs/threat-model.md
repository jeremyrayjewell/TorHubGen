# TorHubGen — Technical Threat Model and Design Constraints

This document is the technical specification for TorHubGen’s operating envelope. If implementation or documentation contradicts this document, the implementation/documentation is nonconforming by definition.

**Audience:** operators and reviewers who already understand Tor onion service limitations.

Normative language: the keywords **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are used as requirement levels.

## Step 1 — System Overview

TorHubGen is a short-lived runtime appliance. A conforming implementation MUST:
- Launch a local Tor process.
- Publish exactly one onion service.
- Host a minimal bulletin-board web app behind the onion service.
- Enforce a fixed lifetime (mandatory; no indefinite mode).
- Attempt teardown and data removal on exit and at expiration.

Optionally, the bulletin board MAY expose a **transient message buffer** (“Temporary Private Messages”) for active participants. If implemented, it MUST be RAM-scoped (or equivalent ephemeral scope) and inherit the same process lifecycle as the board.

Non-goal by design: general-purpose hosting, persistence, identity systems, or feature growth.

## Step 2 — Runtime Lifecycle and Data Volatility

### Runtime Responsibility Boundary

TorHubGen MUST:
- Start Tor.
- Expose exactly one onion service.
- Enforce expiration.
- Attempt teardown and data deletion on normal exit.
- Make teardown failure visible.

TorHubGen MUST NOT claim or imply that it:
- Guarantees deletion under crashes/forced termination/power loss.
- Stops copying/redistribution.
- Prevents harm from compromised hosts.
- Prevents traffic analysis/correlation.
- Determines suitability for a given threat environment.

Teardown is a best-effort cleanup path. It can be skipped or partially executed under crash, power loss, forced termination, kernel panic, or storage failures.

## Step 3 — Out of Scope (Non-Goals)

These items are explicitly out of scope and are not “later improvements.”

- **Endpoints:** compromised devices, browsers, OS/hardware/firmware.
- **Trust failures:** infiltration/coercion; participants leaking URLs/credentials/content; social engineering.
- **Correlation:** traffic analysis, long-term observation, timing/volume correlation.
- **Behavioral identification:** writing style, schedules, metadata, account reuse.
- **Legal/physical outcomes:** immunity, avoiding detention/coercion, raids, compelled disclosure resistance.
- **Availability/reliability:** uptime, DoS resistance, delivery guarantees, scalability.
- **Cryptography/protocols:** custom cryptography, protocol-level changes to Tor, “new systems”.
- **Misuse prevention beyond warnings:** stopping unsafe redeployment, manual lifetime extension, or misuse.
- **Guarantees/suitability claims:** identity concealment/message secrecy guarantees, or claims that use is advisable.
- **Beginner positioning:** “easy” for non-technical users.
- **Persistence/communities:** persistent identities or communities across runs.
- **Moderation/governance:** abuse handling, governance tooling.
- **Clearnet/hybrid:** any clearnet exposure or mixed Tor/non-Tor operation.
- **Persistence beyond declared lifetime:** persisting content, onion service keys, or runtime state beyond the declared duration.
- **Messenger-style private messaging:** persistence/history/inbox; offline delivery; delivery guarantees; end-to-end encryption guarantees; secrecy guarantees beyond Tor transport; identity verification or identity concealment in temporary private messages.

### Rejected Designs

- Auto-renewing onion services or silent persistence.
- Silent defaults that hide risk.
- “One-click” framing or marketing reassurance.
- Persistent identities across runs.

## Step 4 — Attacker Models (Defensive Posture)

A conforming design MUST assume attackers are asymmetric (time/tooling/patience) and that visibility is partial. The design MUST bias toward preventing misconfiguration and persistence.

### A — Opportunistic Network Observer
- The design MUST assume local observation of timing/volume/destination metadata.
- The implementation MUST use Tor-only bindings.
- The system MUST NOT provide clearnet fallback or dual-mode operation.
- The UI/UX SHOULD make Tor-only operation visible.

### B — Passive Long-Term Observer
- The design MUST assume long-term observation and timing/volume correlation.
- The system MUST enforce short lifetimes and discourage reuse.
- The implementation MUST avoid persistent identifiers across runs.

### C — Active Network Interferer (Limited)
- The design MUST assume blocking/throttling/disruption of Tor, DoS, and induced user error.
- Documentation/UX MUST NOT include clearnet fallback guidance.
- The system MUST avoid “temporary debug” modes that create persistence.
- Documentation/UX SHOULD warn against bypass workarounds.

### D — Malicious or Compromised Insider
- The design MUST assume legitimate access with leakage of URLs/credentials/content and logging/copying by participants.
- The system MUST assume leaks and MUST NOT rely on participant discretion.
- One leak MUST NOT compromise future sessions.
- Documentation/UX SHOULD keep group-size assumptions explicit and small.

### E — Post-Compromise Investigator
- The design MUST assume after-the-fact device access to logs/configs/files/timestamps, including legal/coercive authority.
- The implementation SHOULD minimize on-disk artifacts.
- The system MUST make cleanup explicit.
- The system MUST avoid silent logs.

This threat model MUST NOT claim to cover global active adversaries with full network control; endpoint compromise; hardware-level surveillance; coercive disclosure resistance; or large-scale infiltration/Sybil attacks.

## Step 5 — Architecture Decisions (Hard Constraints)

### Ephemeral Appliance Invariants

The runtime appliance MUST:
- Run only for a fixed declared duration (mandatory; no indefinite mode).
- Expose exactly one local web service via Tor, and exactly one onion service.
- Keep runtime state only for the lifetime of execution.
- Generate onion service keys per run.
- Attempt teardown automatically on expiration and termination signals; failure to attempt teardown is an error condition.

Any design that introduces persistence beyond the declared lifetime is invalid by definition.

### Stop-Ship Gate

Treat these as engineering stop conditions:
- Users repeatedly misinterpret constraints despite being shown them.
- Required constraints must be hidden to preserve usability.
- The appliance becomes harder to reason about than manual setup.
- The design lowers the barrier to dangerous misuse (in practice).

### Transient Message Buffer (Temporary Private Messages)

If enabled, temporary private messages are a transient message buffer scoped to the running process (RAM or equivalent ephemeral scope). The implementation MUST satisfy all of the following:
- The buffer MUST be destroyed when the board expires/terminates.
- Messages MUST NOT persist beyond the declared lifetime.
- The system MUST NOT provide an inbox, queue, retries, or offline delivery.
- The system MUST NOT create long-lived identities/accounts/handles.
- Temporary private messages MUST be disabled by default.
- Enabling temporary private messages MUST require explicit startup action.
- Enabling temporary private messages MUST NOT extend the board’s lifetime.

Any temporary private messaging feature that introduces persistence, identity continuity, or expectations of confidentiality is invalid by definition.

## Step 6 — Failure Modes and Operational Limits

Policy: a failure mode is unacceptable if it is silent, confidence-inflating, persistent without awareness, or expands exposure beyond manual Tor usage.

### Design-Level
- **F1 — Silent Persistence:** service outlives lifetime → system MUST enforce explicit expiration; teardown MUST be treated as mandatory; MUST NOT default to “until stopped”; MUST provide co-generated teardown steps.
- **F2 — Overly Abstracted Output:** too opaque to verify → artifacts MUST be plain-text/inspectable and MUST explain what is generated and why.
- **F3 — Implicit Guarantees via UX/Language:** prompts imply reduced risk/guarantees → UX copy MUST avoid guarantee language and MUST present limits at action time.
- **F4 — Accidental Clearnet Exposure:** binds to non-Tor interfaces → bindings MUST be Tor-only; system MUST NOT provide fallback/dual-mode; documentation MUST state expected listening behavior.
- **F10 — Misinterpretation of Transient Message Buffer:** treated as confidential/lower-risk → UI MUST label “Temporary Private Messages”; UI MUST show ephemerality/limits; UI MUST reiterate copying/recording/redistribution and that observation remains possible.

### User-Driven
- **F5 — Reuse Beyond Intended Context:** reuse configs/keys/addresses → system MUST warn against reuse and MUST NOT provide tooling that encourages reuse.
- **F6 — Combining with Unsafe Practices:** risky workflows → system MUST state it does not control user behavior and SHOULD provide non-operational examples.
- **F7 — Misplaced Trust in the Tool:** treated as risk-handling layer → documentation/UX MUST repeat non-goals and MUST avoid language implying guarantees.
- **F11 — Transient Message Buffer Leakage:** recipients copy/record/redistribute → UI MUST warn and MUST NOT imply discretion.

### Environmental
- **F8 — Network Interference/Blocking:** disruption pushes workarounds → documentation MUST NOT include clearnet fallback guidance and MUST warn against “temporary” unsafe changes.
- **F9 — Post-Compromise Discovery:** after-the-fact inspection → implementation SHOULD minimize on-disk artifacts; MUST identify files to delete; MUST avoid unnecessary logs.
- **F12 — Crash/Power Loss:** cleanup doesn’t run → implementation SHOULD minimize writes and narrow ephemeral scope; UX MUST state teardown is best-effort.
- **F13 — Best-Effort Teardown Limitations:** teardown is a cleanup path, not proof of deletion; it cannot execute under power loss/kernel panic and cannot retroactively remove copied data.

Severity policy: prevent clearnet exposure by design; make high-risk failures loud; state inevitable failures plainly.

## Step 7 — Operational Reality (Irreducible Constraints)

The following are implementation/UX constraints. They MUST appear in user-facing material at startup/config time and in the running instance UI (include the temporary private messages warning if enabled):

- The appliance does not provide identity concealment or message secrecy guarantees.
- Compromised devices negate network-path properties.
- Other participants can copy, record, or redistribute content.
- Identification through behavior remains possible.
- Legal/physical consequences remain possible.
- Temporary services become riskier when they persist; teardown is best-effort, not guaranteed.
- Temporary private messages exist only while the board is running, are not confidential, and can be copied/recorded/redistributed by recipients.

### Disallowed Statements (Documentation/UX)

Documentation/UX MUST NOT claim or imply guarantees, “lower-risk” operation, confidentiality for temporary private messages, marketing reassurance (e.g., “hardened”, “set and forget”, “one-click”), or beginner-friendly suitability.