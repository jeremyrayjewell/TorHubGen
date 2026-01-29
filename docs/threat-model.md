# Threat Model
This document defines the limits, risks, and ethical boundaries of the project before any code exists. It exists to prevent the tool from creating false confidence or increasing harm through misuse. Code that violates this document is considered incorrect by definition.

**Intended audience:** This document is written for technically competent users who already understand Tor’s limitations. It is not a recommendation to use Tor, onion services, or this tool in any context. The existence of this tool does not imply that its use is advisable in any given situation.

## Step 1 — Problem Statement

TorHubGen reduces avoidable setup/teardown mistakes when running ad-hoc, short-lived group communication under elevated risk. The core problem is operational error under stress (especially teardown), not adding communication features.

TorHubGen is a short-lived runtime appliance: it launches a local Tor process and publishes exactly one onion service, hosts a minimal bulletin-board web app behind that onion service, may optionally provide ephemeral session-scoped temporary private messages between active participants, enforces a fixed lifetime chosen at startup (required; no indefinite mode), and attempts teardown and data removal on exit and at expiration.

If enabled, temporary private messages exist only for the lifetime of the running instance and do not change the primary bulletin-board goal.

It is not a general-purpose hosting platform, persistent forum, messaging platform, or community system.

## Step 2 — Ethical Framing

False confidence is treated as a hazard; over-capability is treated as risk. Simplicity and explicit limitation are requirements. If TorHubGen cannot reduce net risk compared to manual setup, it should not exist.

### Runtime Responsibility Boundary

- **TorHubGen does:** start Tor, expose exactly one onion service, enforce expiration, attempt teardown/data deletion on normal exit, and make teardown failure visible.
- **TorHubGen does not:** guarantee deletion under crashes/forced termination/power loss; stop copying/redistribution; prevent harm from compromised hosts; prevent traffic analysis/correlation; determine suitability for a given threat environment.

Teardown is attempted, not guaranteed.

## Step 3 — Explicit Non-Goals

TorHubGen does not solve or prevent the following classes of problems. These are not “limitations to fix later”; they are scope boundaries.

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
- **Persistence beyond lifetime:** persisting content, onion service keys, or runtime state beyond the declared duration.
- **Messenger-style private messaging:** persistence/history/inbox; offline delivery; delivery guarantees; end-to-end encryption guarantees; secrecy guarantees beyond Tor transport; identity verification or identity concealment in temporary private messages.

### Explicit Rejections (Design-Level)

The following must not be added later (even if requested):
- “One-click” framing or marketing reassurance
- Claims that use is “lower-risk than Tor alone”
- Auto-renewing onion services, silent persistence, or silent defaults
- Persistent identities across runs or beginner-friendly positioning

## Step 4 — Guiding Principles and Attacker Models

Assume asymmetric power and partial visibility; assume human error dominates; avoid designing for “ultimate adversaries” if doing so increases user risk or false confidence.

### Attacker Model A — Opportunistic Network Observer
- **Capabilities:** local observation of timing/volume/destination metadata.
- **Design:** prevent non-Tor bindings; avoid dual-homing/clearnet fallback; make Tor-only operation default and visible.

### Attacker Model B — Passive Long-Term Observer
- **Capabilities:** long-term observation and timing/volume correlation.
- **Design:** discourage reuse; default to short lifetimes; avoid persistent identifiers; make teardown explicit.

### Attacker Model C — Active Network Interferer (Limited)
- **Capabilities:** blocks/throttles/disrupts Tor; DoS; induces user error.
- **Design:** refuse clearnet fallback; avoid “temporary debug” modes that persist; warn against bypass.

### Attacker Model D — Malicious or Compromised Insider
- **Capabilities:** legitimate access; leaks URLs/credentials/content; logs/copies data.
- **Design:** assume leaks; avoid one leak compromising future sessions; avoid persistent identities/shared secrets; keep group-size assumptions explicit and small.

### Attacker Model E — Post-Compromise Investigator
- **Capabilities:** after-the-fact device access; inspects logs/configs/files/timestamps; may have legal/coercive authority.
- **Design:** minimize on-disk artifacts; make cleanup explicit; avoid silent logs; prefer stateless/easily purged outputs.

### Explicitly Out-of-Scope Adversaries

Out of scope: global active adversaries with full network control; endpoint compromise; hardware-level surveillance; coercive disclosure resistance; large-scale infiltration or Sybil attacks.

## Step 5 — Risks and Design Constraints

### Framing Principle
TorHubGen may exist only if it reduces avoidable operational mistakes without increasing user confidence beyond what Tor provides or expanding threat surface. Any risk introduced or amplified by TorHubGen is presumptively unacceptable unless explicitly justified and mitigated.

### Acceptable Risks
These risks are acknowledged and unavoidable; TorHubGen must not imply it removes them.

Residual network-level risk (correlation/traffic analysis), insider misuse, endpoint compromise, unsafe user behavior (reuse/ignored teardown/risky workflows), and service disruption/DoS remain possible.

### Unacceptable Risks (Hard Stops)

These risks must not be introduced, increased, or obscured by TorHubGen. If they are, the design must change or the feature must be removed.

- **U1 (false confidence):** language/UX implying guarantees, reduced identification likelihood, insider-misuse prevention, or avoided legal/physical consequences.
- **U2 (silent persistence):** service/keys/config surviving past lifetime, auto-renewal, “just keep running”; ephemerality must fail closed.
- **U3 (scope creep):** accounts/handles, identity continuity, or messenger-style properties (beyond the bulletin board + constrained temporary private messages).
- **U4 (threat-surface expansion):** clearnet fallback, mixed Tor/non-Tor, unsafe flags, convenience bypass; no “expert-only” unsafe modes.
- **U5 (normalization):** implied recommendation, beginner-appropriate framing, lowering the barrier to uninformed use.
- **U6 (responsibility transfer):** implying the tool “handles” risk or shifting responsibility to software.

### Risk That Triggers Project Pause or Redesign
The project should pause or halt if:
- Users repeatedly misunderstand guarantees despite documentation
- Reviewers identify unavoidable false-confidence effects
- The appliance becomes harder to reason about than manual setup
- Safety warnings must be hidden to preserve usability
- The tool meaningfully lowers the barrier to dangerous behavior
If any of these occur, pausing or not shipping is the correct outcome.

### Ephemeral Appliance Architecture
The system is an ephemeral runtime appliance with non-negotiable constraints: it runs only for a fixed declared duration (mandatory; no indefinite mode), exposes exactly one local web service via Tor, keeps runtime state only for the lifetime of execution, generates onion service keys per run, performs teardown automatically on expiration/termination signals, and treats failure to attempt teardown as an error condition.

Any design that introduces persistence beyond the declared lifetime is invalid by definition.

Value is reducing missed teardown and lifecycle mistakes, not adding guarantees.

### Ephemeral Private Messaging Constraints
If temporary private messages are supported, they must be ephemeral within the same data scope as the board (in-memory or equivalent), be destroyed when the board expires/terminates, never persist beyond the declared lifetime, have no inbox/queue/retry/offline delivery, create no long-lived identities/accounts/handles, be disabled by default and only enabled by explicit user action at startup, and must not extend the board’s lifetime.

Any private messaging feature that introduces persistence, identity continuity, or expectations of confidentiality is invalid by definition.

### Human-Factors Constraints
Assume users are stressed/tired/afraid and may not read carefully. Defaults must be conservative; risky options must require friction; failure must be obvious.

### Definition of “Minimum” (Litmus Test)
Keep components that reduce setup error or risk. Remove components that increase confidence without real risk reduction, or add complexity without safety value.

## Step 6 — Failure Modes

### Policy
- Unacceptable if silent, confidence-inflating, persistent without awareness, or expands exposure beyond manual Tor usage.
- Tolerable only if visible/discoverable, not worse than manual setup, and pushes toward teardown rather than continuation.

### Design-Level Failure Modes (introduced by TorHubGen)

- **F1 — Silent Persistence:** service outlives lifetime → require explicit expiration, mandatory teardown framing, no “until stopped”, co-generated teardown steps.
- **F2 — Overly Abstracted Output:** too opaque to verify → require plain-text/inspectable artifacts and explanations.
- **F3 — Implicit Guarantees via UX/Language:** prompts imply reduced risk/guarantees → avoid guarantee language; show limits at action time.
- **F4 — Accidental Clearnet Exposure:** binds to non-Tor interfaces → Tor-only bindings; no fallback/dual-mode; document expected listening.
- **F10 — Misinterpretation of Temporary Private Messages:** users treat as confidential/lower-risk → label “Temporary Private Messages”; show ephemerality/limits in UI; reiterate copying/recording/redistribution and observation remains possible.

### User-Driven Failure Modes (outside tool control)

- **F5 — Reuse Beyond Intended Context:** reuse configs/keys/addresses → warn against reuse; no tooling that encourages reuse.
- **F6 — Combining with Unsafe Practices:** risky workflows → state tool doesn’t control behavior; give non-operational examples.
- **F7 — Misplaced Trust in the Tool:** treated as risk-handling layer → repeat non-goals; emphasize assistance, not guarantees.
- **F11 — Temporary Private Message Leakage:** recipients copy/record/redistribute → warnings; no language implying discretion.

### Environmental Failure Modes

- **F8 — Network Interference/Blocking:** disruption pushes workarounds → no clearnet fallback guidance; warn against “temporary” unsafe changes.
- **F9 — Post-Compromise Discovery:** after-the-fact inspection → minimize on-disk artifacts; identify files to delete; avoid unnecessary logs.
- **F12 — Abrupt Termination (Crash/Power Loss):** cleanup doesn’t run → minimal writes; narrow ephemeral scope; warn teardown is attempted, not guaranteed.
- **F13 — Over-Trust in Teardown:** teardown treated as proof → best-effort language; visible failure when detectable; avoid “guaranteed deletion”.

### Severity Policy
- Catastrophic failures (e.g., clearnet exposure) must be prevented by design.
- High-risk failures must be loud and unavoidable.
- Inevitable failures must be stated plainly.
- Silent acceptance of risk is not acceptable.

## Step 7 — Safety Language

Safety language must reduce false confidence, state limits plainly, and appear at moments of action (startup/UI), not only in docs.

### Mandatory Safety Statements (Irreducible)

The following statements—or functionally equivalent language—must appear in user-facing material:

> “TorHubGen helps reduce configuration mistakes when running a short-lived onion-service bulletin board appliance.
> It does not provide identity concealment or message secrecy guarantees.”
>
> “This tool does not prevent harm if your device is compromised.”
> “This tool does not prevent other participants from copying or redistributing content.”
> “This tool does not prevent identification through behavior.”
> “This tool does not prevent legal or physical consequences.”
>
> “Temporary services become dangerous when they persist.”
> “If you do not tear this down, risk increases over time.”
> “Teardown is attempted, not guaranteed.”
>
> “Using this tool does not transfer responsibility for risk management away from you.”
> “The appliance cannot evaluate your threat environment.”
>
> “Temporary private messages exist only while this board is running.
> They are not confidential.
> Other participants can copy, record, or redistribute them.”

### Language That Must Be Avoided (Hard Prohibitions)

Not allowed: guarantees or implied guarantees (including “lower-risk” claims), any claim that temporary private messages are confidential/lower-risk than public posting, marketing reassurance (e.g., “hardened”, “military-grade”, “set and forget”, “one-click”), or beginner-friendly positioning implying suitability.

### Placement Requirements

Safety language must appear in threat-model.md, the README, at startup/config time, and in the running instance UI (include the temporary private messages warning if enabled).

### Safety Language as a Change Gate

Any change that removes warnings, softens limitations, improves perceived safety without real changes, or improves usability at the cost of clarity must be treated as a security regression.