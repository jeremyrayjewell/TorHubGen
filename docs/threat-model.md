# Threat Model
This document defines the limits, risks, and ethical boundaries of the project before any code exists. It exists to prevent the tool from creating false confidence or increasing harm through misuse. Code that violates this document is considered incorrect by definition.

**Intended audience:** This document is written for technically competent users who already understand Tor’s limitations. It is not a recommendation to use Tor, onion services, or this tool in any context. The existence of this tool does not imply that its use is advisable in any given situation.

## Step 1 — Problem Statement

TorHubGen addresses the problem of ad-hoc, short-lived group communication setup under elevated risk, where manual Tor service setup and teardown is error-prone and operational mistakes materially increase user exposure.

The core problem is setup risk, not communication itself.

### More Explicitly

For small, trusted groups who already intend to use Tor onion services:
- Manually creating temporary onion services
- Configuring access controls
- Coordinating credentials or URLs
- Ensuring expiration and teardown

...is cognitively demanding, repetitive, and highly susceptible to human error.

These errors often include:
- Reusing onion addresses longer than intended
- Forgetting to rotate keys
- Accidentally exposing services beyond the intended group
- Leaving services running after the threat window ends
- Misunderstanding Tor’s protections and limitations
- Overestimating what Tor alone provides

TorHubGen exists to reduce *avoidable operational mistakes* during setup and teardown.

### What the Tool Actually Does

TorHubGen is a short-lived runtime appliance. When started, it:
- Launches a local Tor process and publishes exactly one onion service
- Hosts a minimal bulletin-board-style web application behind that onion service
- The hosted bulletin board may optionally support ephemeral, session-scoped temporary private messages between active participants
- Enforces a fixed lifetime chosen at startup (required; no indefinite mode)
- Attempts automated teardown and data removal on exit and at expiration

If enabled, temporary private messages exist only for the lifetime of the running instance. They are not a core feature and do not change the primary bulletin-board function.

It is explicitly not:
- A general-purpose hosting platform
- A persistent forum system
- A messaging platform
- A user-growth or community platform

### What This Is Not Solving

This tool does not:
- Provide anonymity or confidentiality guarantees
- Prevent harm from compromised endpoints
- Prevent infiltration of trusted groups
- Prevent traffic analysis or correlation
- Defeat state-level surveillance
- Prevent risky user behavior outside the tool
- Make Tor approachable or appropriate for non-technical users
Those are different problems and explicitly out of scope.

A technically competent user could reproduce the same runtime system manually, but would be more likely to forget teardown or lifecycle limits.

### Why This Problem Is Legitimate

The gap TorHubGen targets exists because:
- Tor documentation assumes high operator competence
- Many real users operate under stress, fatigue, or fear
- Copy-paste guides encourage unsafe reuse patterns
- “Temporary” infrastructure often becomes permanent accidentally
- Existing tools optimize for convenience or uptime, not ephemerality
The harm model here is **unforced error**, not cryptographic failure.

## Step 2 — Ethical Framing

This project treats:
- False confidence as a hazard
- Over-capability as a risk
- Simplicity as a safety feature
- Explicit limitation as a requirement
If TorHubGen cannot reduce net risk compared to manual setup, it should not exist.

### Runtime Responsibility Boundary

TorHubGen is responsible for:
- Starting the Tor process it launches
- Exposing exactly one onion service
- Enforcing the declared expiration time
- Attempting teardown and data deletion on normal exit
- Making teardown failure visible to the user

TorHubGen is not responsible for:
- Guaranteeing data deletion under crashes, forced termination, or power loss
- Preventing users from copying or redistributing content
- Preventing harm from compromised hosts
- Preventing traffic analysis or correlation
- Determining whether use is appropriate for a given threat environment

This boundary is intentionally uncomfortable: teardown is attempted, not guaranteed.

## Step 3 — Explicit Non-Goals

TorHubGen does not solve or provide protection against:

1. **Endpoint Compromise**
   - Malware on participant devices
   - Keylogging, screen capture, memory scraping
   - Compromised operating systems or browsers
   - Hardware implants or firmware attacks
   - Rationale: Tor protects network paths, not endpoints. Any implication otherwise is dangerous.

2. **Trust Failures Within the Group**
   - Infiltration by a malicious participant
   - Participants leaking URLs, credentials, or content
   - Coercion or compromise of trusted members
   - Social engineering inside the group
   - Rationale: TorHubGen assumes trusted membership, not trustworthiness enforcement.

3. **Traffic Analysis and Correlation**
   - Global passive adversaries
   - Timing correlation attacks
   - Volume-based inference
   - Long-term observation across sessions
   - Rationale: Tor reduces some risks but does not eliminate correlation. Temporary services help, but do not negate this class of attack.

4. **Identity Exposure Through User Behavior**
   - Logging into personal accounts while connected
   - Reusing usernames, writing style, or metadata
   - Copying content across contexts
   - Time-of-day patterns
   - Language or cultural fingerprints
   - Rationale: Behavioral deanonymization is outside the tool’s control.

5. **Legal, Policy, or Physical Outcomes**
   - Legal immunity
   - Protection from arrest, detention, or coercion
   - Safety from physical surveillance or raids
   - Protection from compelled disclosure
   - Rationale: Technical tools cannot provide these protections. Suggesting otherwise is unethical.

6. **High-Availability or Reliability Guarantees**
   - Continuous uptime
   - Resistance to DoS
   - Message delivery guarantees
   - Scalability beyond small groups
   - Rationale: Ephemerality and safety conflict with availability. Safety wins.

7. **Cryptographic Novelty or Innovation**
   - New anonymity techniques
   - Custom cryptography
   - Protocol-level enhancements to Tor
   - Rationale: Novel crypto increases risk. TorHubGen is strictly a composition and configuration tool.

8. **Misuse Prevention Beyond Warnings**
   - Stopping users from using the output incorrectly
   - Preventing users from extending lifetime manually
   - Preventing redeployment in unsafe contexts
   - Rationale: The tool can discourage misuse, not enforce compliance.

9. **Guarantees and Suitability Claims**
    - Providing anonymity, confidentiality, or suitability guarantees
    - Rationale: Claims of guarantees create false confidence.

10. **Beginner-Targeted Positioning**
    - Making Tor “easy” or appropriate for non-technical users
    - Rationale: Lowering friction without transferring understanding increases misuse.

11. **Long-Term Communities or Identities**
    - Supporting long-term communities
    - Supporting persistent identities across runs
    - Rationale: Identity continuity increases correlation and normalization risk.

12. **Moderation, Abuse Handling, or Governance Tools**
    - Moderation workflows
    - Abuse reporting or handling
    - Governance features for communities
    - Rationale: These expand responsibility and shift the tool toward a platform.

13. **Clearnet Access or Hybrid Modes**
    - Any clearnet access
    - Any mixed Tor/non-Tor modes
    - Rationale: Dual exposure materially increases user error and risk.

14. **Persistence Beyond Declared Lifetime**
    - Persisting content beyond the declared lifetime
    - Reusing onion service keys across runs
    - Rationale: Persistence undermines ephemerality by definition.

15. **Messenger-Style Private Messaging**
    - Persistent temporary private messaging
    - Message history, inboxes, or archives
    - Offline delivery or guaranteed delivery
    - End-to-end encryption guarantees
    - Confidentiality guarantees beyond Tor transport
    - Identity verification or protection in private messages
    - Rationale: These properties create a messenger-style system and expectations of confidentiality that TorHubGen does not and cannot provide.

### Explicit Rejections (Design-Level)

The following must not be added later:
- “One-click messaging” framing
- Claims of hardened anonymity
- “Lower-risk than Tor alone” marketing language
- Auto-renewing onion services
- Persistent identities across generations
- Silent defaults that hide risk
- “Beginner-friendly” positioning that implies suitability
If a feature reduces friction by hiding complexity, it is suspect.

### Non-Goals That Must Appear in Documentation

These statements should be unavoidable in user-facing material:
- “This tool does not prevent harm from compromised devices.”
- “This tool does not prevent identification through behavior.”
- “This tool does not provide anonymity or confidentiality guarantees.”
- “This tool does not prevent participants from copying or redistributing content.”
- “This tool does not prevent legal or physical consequences.”

If users skip these warnings, that is acceptable.
If the tool omits them, that is not.

### Why This Matters

Most harm in this domain comes from:
- Overgeneralization of Tor’s guarantees
- Tool-induced confidence
- Gradual scope expansion without threat review
By locking non-goals early, we create a scope firewall.

## Step 4 — Guiding Principles and Attacker Models

- Assume asymmetric power: attackers often have more time, tooling, and patience.
- Assume partial visibility, not omniscience.
- Assume human error is the dominant failure vector.
- Avoid designing for “ultimate adversaries” if doing so increases user risk or false confidence.

### Attacker Model A — Opportunistic Network Observer
Capabilities:
- Can observe traffic at one or more local network points
- Can see timing, volume, and destination metadata (not payload)
- Cannot break Tor encryption
- Cannot observe the entire Tor network
Examples (abstract):
- ISP-level monitoring
- Local network administrators
- Shared Wi-Fi operators
Relevance to TorHubGen:
- Tor already mitigates much of this risk
- Configuration mistakes (e.g., clearnet exposure, wrong bindings) can reintroduce it
- Temporary services reduce exposure window
**Design Implication:**
TorHubGen should:
- Prevent accidental non-Tor bindings
- Avoid dual-homing or fallback to clearnet
- Make “Tor-only” operation the default and visible

### Attacker Model B — Passive Long-Term Observer
Capabilities:
- Observes traffic over extended periods
- Performs timing and volume correlation
- Does not control endpoints
- Does not actively interfere
Examples (abstract):
- Large-scale monitoring entities
- Organizations with long retention policies
Relevance to TorHubGen:
- Ephemerality matters here
- Reuse and longevity dramatically increase risk
- Consistent schedules and patterns leak information
**Design Implication:**
TorHubGen should:
- Strongly discourage reuse
- Default to short lifetimes
- Avoid persistent identifiers
- Make teardown explicit, not optional

### Attacker Model C — Active Network Interferer (Limited)
Capabilities:
- Can block, throttle, or disrupt Tor traffic
- Can attempt denial-of-service
- Can induce user error through disruption
- Cannot reliably deanonymize Tor users
Examples (abstract):
- Network censors
- Adversaries applying pressure through instability
Relevance to TorHubGen:
- Users may respond to disruption by “temporarily” weakening setup
- Convenience-driven bypasses are dangerous
**Design Implication:**
TorHubGen must:
- Refuse to generate fallback-to-clearnet configs
- Avoid “temporary debug” modes that persist
- Surface warnings when users attempt to bypass Tor

### Attacker Model D — Malicious or Compromised Insider
Capabilities:
- Has legitimate access to the onion address
- Can leak URLs, credentials, or content
- Can log activity or copy data
- Can act patiently and selectively
Relevance to TorHubGen:
- This is one of the most realistic threats
- Technical controls offer limited mitigation
**Design Implication:**
TorHubGen should:
- Assume insiders can leak
- Avoid designs where one leak compromises future sessions
- Avoid persistent identities or shared secrets across generations
- Make group size assumptions explicit and small

### Attacker Model E — Post-Compromise Investigator
Capabilities:
- Gains access to a participant device after the fact
- Can inspect logs, configs, files, and timestamps
- May have legal or coercive authority
Relevance to TorHubGen:
- Residual data is dangerous
- “Temporary” must mean erasable
**Design Implication:**
TorHubGen should:
- Minimize on-disk artifacts
- Make cleanup steps explicit and unavoidable
- Avoid silent log generation
- Prefer stateless or easily purged outputs

### Explicitly Out-of-Scope Adversaries

TorHubGen is not designed to withstand:
- Global active adversaries with full network control
- Endpoint compromise before or during use
- Hardware-level surveillance
- Coercive disclosure resistance
- Large-scale infiltration or Sybil attacks

Designing for these would require:
- Different tools
- Different tradeoffs
- Dangerous claims

## Step 5 — Risks and Design Constraints

### Framing Principle
TorHubGen may only exist if, on balance, it:
- Reduces avoidable operational mistakes
- Does not increase user confidence beyond what Tor already provides
- Does not meaningfully expand user threat surface
If a risk is introduced or amplified by TorHubGen, it is presumptively unacceptable unless explicitly justified and mitigated.

### Acceptable Risks
These risks are acknowledged, unavoidable, and not worsened by TorHubGen.

A. Residual Network-Level Risk
    Correlation attacks remain possible
    Traffic analysis remains possible
    Tor’s threat model limits still apply
**Justification:** TorHubGen does not claim to reduce these risks; it only avoids reintroducing worse ones through misconfiguration.

B. Insider Misuse or Betrayal
    Participants may leak onion addresses
    Participants may copy or archive content
    Participants may act maliciously or negligently
**Justification:** Trusted-group assumptions are explicit. The tool does not claim to manage trust.

C. Endpoint Compromise
    Malware, OS compromise, or device seizure defeats protections
    Generated artifacts may be discovered post-compromise
**Justification:** TorHubGen does not increase endpoint risk and explicitly warns about this limitation.

D. User Error Outside Generator Control
    Users may ignore teardown steps
    Users may redeploy output unsafely
    Users may combine outputs with risky workflows
**Justification:** The tool reduces error probability but cannot eliminate it. Warnings are provided.

E. Service Disruption
    Onion services may be unavailable
    Connections may be unstable
    DoS is possible
**Justification:** Availability is not a safety goal. No guarantees are made.

### Unacceptable Risks (Hard Stops)

These risks must not be introduced, increased, or obscured by TorHubGen. If they are, the design must change or the feature must be removed.

U1. False Confidence Risk
    Any feature or language that causes users to believe:
    They have anonymity guarantees
    They are unlikely to be identified
    Insider misuse is prevented
    Legal or physical consequences are prevented
**Status:** Unacceptable under all circumstances.
**Implication:** Features that *feel* reassuring but do not add real protection are rejected.

U2. Silent Persistence Risk
    Onion services surviving past intended lifetime
    Keys or configs persisting without explicit user awareness
    Auto-renewal or “just keep running” behavior
**Status:** Unacceptable.
**Implication:** Ephemerality must fail closed, not open.

U3. Scope Creep into Messaging or Identity
    Adding messaging protocols
    Adding user accounts or handles
    Adding identity continuity across sessions
**Status:** Unacceptable.
**Implication:** TorHubGen is a bulletin-board appliance only. Communication layers are out of scope.

U4. Covert Expansion of Threat Surface
    Optional clearnet fallbacks
    Mixed Tor/non-Tor modes
    “Debug” or “temporary” unsafe flags
    Convenience shortcuts that bypass Tor
**Status:** Unacceptable.
**Implication:** There are no “expert-only” unsafe modes.

U5. Normalization of Dangerous Use
    Positioning the tool as beginner-appropriate
    Encouraging use by people who do not understand the risks
    Framing that implies this is a default or recommended solution
**Status:** Unacceptable.
**Implication:** The tool must actively discourage casual or uninformed use.

U6. Ambiguous Responsibility Transfer
    Language implying the tool “handles security”
    Shifting responsibility away from users
    Treating safety as a property of the software
**Status:** Unacceptable.
**Implication:** Responsibility boundaries must remain explicit and uncomfortable.

### Risk That Triggers Project Pause or Redesign
The project should pause or halt if:
- Users repeatedly misunderstand guarantees despite documentation
- Reviewers identify unavoidable false-confidence effects
- The appliance becomes harder to reason about than manual setup
- Safety warnings must be hidden to preserve usability
- The tool meaningfully lowers the barrier to dangerous behavior
At that point, not shipping is the correct outcome.

### Risk Acceptance Is Explicit, Not Implicit
No risk is considered accepted unless:
- It is documented here
- Its justification is written
- Its mitigation is stated or explicitly declined
“Everyone knows this” is not a valid argument.

### Step 5 Outcome
After this step:
- We know what harm we tolerate
- We know what harm we refuse
- We have a clear veto framework for future decisions
This is the ethical backbone of the project.

### Governing Principle
**Every additional feature is a liability unless it demonstrably reduces user harm.**
The minimum viable design (MVD) is not about usefulness or adoption. It is about reducing setup mistakes without introducing new confidence or complexity. If the generated output increases risk compared to manual setup, the design has failed.

### Ephemeral Appliance Architecture

The system is an ephemeral runtime appliance with the following non-negotiable constraints:
- The system runs only for a fixed, declared duration.
- The duration is mandatory; no indefinite mode exists.
- Exactly one local web service is exposed via Tor.
- All runtime state exists only for the lifetime of execution.
- Onion service keys are freshly generated per run.
- Teardown is automatic on expiration or termination signals.
- Failure to attempt teardown is treated as an error condition.

Any design that introduces persistence beyond the declared lifetime is invalid by definition.

This architecture is intentionally narrow. A technically competent user could implement the same system manually; the value of TorHubGen is in reducing missed teardown and lifecycle mistakes, not in adding new guarantees.

### Ephemeral Private Messaging Constraints

If temporary private messages are supported, they must obey all of the following constraints:
- Messages exist only in memory or within the same ephemeral data scope as the board.
- Messages are destroyed automatically when the board expires or terminates.
- No temporary private messages persist beyond the declared lifetime.
- No inboxes, queues, retries, or offline delivery exist.
- No long-lived identities, accounts, or handles are created.
- Temporary private messaging is disabled by default.
- Enabling temporary private messaging requires explicit user action at startup.
- Temporary private messaging must not extend the board’s lifetime.

Any private messaging feature that introduces persistence, identity continuity, or expectations of confidentiality is invalid by definition.

### Human-Factors Constraints
The design must assume users:
- Are stressed
- Are tired
- Are afraid
- May not read everything carefully
Therefore:
- Risk-increasing options must be hard to enable accidentally
- Dangerous options must require friction
- Defaults must be conservative, not flexible
- Failure should be obvious, not silent

### Definition of “Minimum” (Litmus Test)
If we remove a component and:
- Setup becomes more error-prone → keep it
- Risk increases → keep it
- Confidence increases without protection → remove it
- Complexity increases without safety → remove it
This test should be applied repeatedly.

## Step 6 — Failure Modes

### 6.1 Framing Principle

A failure mode is unacceptable if it:
- Is silent
- Creates false confidence
- Persists without user awareness
- Expands exposure beyond manual Tor usage

A failure mode is tolerable only if:
- It is visible or discoverable
- It does not worsen the user’s position compared to manual setup
- It encourages teardown rather than continuation

### 6.2 Failure Mode Categories
We classify failures into design failures, user failures, and environmental failures.
All three must be anticipated.

### 6.3 Design-Level Failure Modes

These are failures introduced by TorHubGen itself.

### F1 — Silent Persistence
- **Description:** Generated onion service continues running past its intended lifetime due to misconfigured expiration, user inaction, or unclear teardown.
- **Risk:** Extended exposure increases correlation and discovery risk.
- **Mitigation requirements:**
    - Expiration must be explicit and time-bounded
    - Teardown instructions must be co-generated
    - No defaults that imply “until stopped”
    - Documentation must treat teardown as mandatory, not optional
- **Residual risk:** User may still ignore teardown. This is acknowledged, not solved.

### F2 — Overly Abstracted Output
- **Description:** Generated configuration is too opaque for users to understand what is running or why.
- **Risk:** Users trust the tool instead of understanding the setup, increasing misuse.
- **Mitigation requirements:**
    - Outputs must be inspectable as plain text
    - No binary blobs or opaque bundles
    - Comments explaining what is generated and why

### F3 — Implicit Guarantees via UX or Language
- **Description:** Tool wording, prompts, or defaults imply reduced risk, anonymity guarantees, or confidentiality.
- **Risk:** False confidence leads to riskier behavior.
- **Mitigation requirements:**
    - Avoid language that implies guarantees, confidentiality, or reduced risk
    - Include explicit limitation statements at generation time
    - Treat reassurance as a hazard

### F4 — Accidental Clearnet Exposure
- **Description:** Misconfiguration results in services binding to non-Tor interfaces.
- **Risk:** Immediate deanonymization.
- **Mitigation requirements:**
    - Explicit Tor-only bindings
    - No fallback or dual-mode options
    - Clear documentation of expected listening behavior

This failure mode is catastrophic and must be treated with highest priority.

### F10 — Misinterpretation of Private Messaging

- **Description:** Users treat temporary private messages as confidential or lower-risk than public posts.
- **Risk:** Users share sensitive information under false assumptions.
- **Mitigation requirements:**
    - Label the feature explicitly as “Temporary Private Messages”
    - Display ephemerality and limitation warnings inside the temporary private messaging interface
    - Reiterate that messages may be copied, recorded, or observed
- **Residual risk:** Users may still assume confidentiality. This is acknowledged, not solved.

### 6.4 User-Driven Failure Modes

These failures occur due to user behavior outside the tool’s control.

### F5 — Reuse Beyond Intended Context
- **Description:** Users reuse generated configs, keys, or onion addresses for convenience.
- **Risk:** Correlation across sessions; expanded attack surface.
- **Mitigation requirements:**
    - Explicit warnings against reuse
    - No tooling to encourage or simplify reuse
    - Documentation framing reuse as dangerous, not advanced

### F6 — Combining with Unsafe Practices
- **Description:** Users combine TorHubGen output with risky workflows (personal accounts, shared machines, logging, etc.).
- **Risk:** Behavioral deanonymization.
- **Mitigation requirements:**
    - Clear statements that the tool does not manage user behavior
    - Examples of common unsafe combinations (without operational detail)

### F7 — Misplaced Trust in the Tool
- **Description:** Users treat TorHubGen as a protective layer rather than a mistake-reduction aid.
- **Risk:** Expanded reliance increases harm when assumptions fail.
- **Mitigation requirements:**
    - Repetition of non-goals
    - Language emphasizing assistance, not protection
    - Avoid branding that implies safety

### F11 — Private Message Leakage

- **Description:** Recipients copy, screenshot, record, or redistribute temporary private messages.
- **Risk:** Exposure identical to public content leakage.
- **Mitigation requirements:**
    - Explicit warnings that temporary private messages do not prevent recipients from copying, recording, or redistributing them
    - No language implying trust or discretion

### 6.5 Environmental Failure Modes
These arise from the broader environment.

### F8 — Network Interference or Blocking
- **Description:** Tor traffic is disrupted, leading users to seek workarounds.
- **Risk:** Users weaken setup or bypass Tor.
- **Mitigation requirements:**
    - No documentation suggesting clearnet fallback
    - Warnings against “temporary” unsafe changes

### F9 — Post-Compromise Discovery
- **Description:** An adversary gains access to a device after use and inspects residual data.
- **Risk:** Retroactive exposure.
- **Mitigation requirements:**
    - Minimize on-disk artifacts
    - Explicit identification of files to delete
    - Avoid unnecessary logs

### 6.6 Failure Mode Severity Policy

- Catastrophic failures (e.g., clearnet exposure) must be prevented by design.
- High-risk failures must be loud and well-documented.
- Inevitable failures must be acknowledged and framed honestly.
- Silently accepting risk is never acceptable.

### 6.7 Failure as a Design Signal

If preventing a failure mode requires:
- Hiding information
- Increasing abstraction
- Increasing complexity
- Adding automation that users don’t understand

...then the design is likely unsafe.

## Step 7 — Safety Language

If users misunderstand what the tool does, the tool has failed—regardless of technical correctness.

Safety language must:
- Reduce false confidence
- Be explicit about limits
- Avoid reassuring tone
- Prefer clarity over comfort
- Be repeated at moments of action, not buried

### 7.2 Mandatory Safety Statements (Irreducible)

The following statements—or functionally equivalent language—must appear:

### A. Scope and Purpose

> “TorHubGen helps reduce configuration mistakes when running a short-lived onion-service bulletin board appliance.
> It does not provide anonymity or confidentiality guarantees.”

### B. Non-Protection Warnings

> “This tool does not prevent harm if your device is compromised.”
> “This tool does not prevent other participants from copying or redistributing content.”
> “This tool does not prevent identification through behavior.”
> “This tool does not prevent legal or physical consequences.”

These must be plain statements, not footnotes or conditionals.

### C. Ephemerality Warning

> “Temporary services become dangerous when they persist.”
> “If you do not tear this down, risk increases over time.”

This language should frame teardown as risk reduction, not housekeeping.

### D. Responsibility Boundary

> “Using this tool does not transfer responsibility for risk management away from you.”
> “The appliance cannot evaluate your threat environment.”

### Private Messaging Warning

> “Temporary private messages are temporary and exist only while this board is running.
> They are not confidential.
> Other participants can copy, record, or redistribute them.”

Avoid phrases that suggest the tool “handles” or “manages” risk.

### 7.3 Language That Must Be Avoided (Hard Prohibitions)

The following terms or implications are not allowed anywhere:
- Claims of anonymity or confidentiality guarantees
- Claims that temporary private messages are confidential or lower-risk than public posting
- Marketing-style reassurance
- “Hardened” or “military-grade” claims
- “Beginner-friendly” positioning that implies suitability
- “One-click” framing
- “Set and forget” framing

If a sentence feels reassuring, it should be rewritten.

### 7.4 Tone Requirements

Safety language must be:
- Calm
- Direct
- Non-alarmist
- Non-promotional
- Non-condescending

It should not:
- Encourage use
- Discourage fear
- Suggest confidence
- Minimize risk

Neutral honesty is the target.

### 7.5 Placement Requirements

Safety language must appear:
- In threat-model.md (authoritative, complete)
- In the README (condensed, unavoidable)
- At generation time (action-linked warnings)
- In generated instance documentation (context-specific reminders)

If a user can generate output without seeing limitations, that is a failure.

### 7.6 Repetition Is a Feature

It is acceptable—and desirable—for users to see the same warnings multiple times.

Repetition counters:
- Stress
- Fatigue
- Overconfidence
- Selective reading

Variation in wording is acceptable; dilution is not.

### 7.7 Example “Last-Chance” Warning (Conceptual)

Before output is produced, the tool should present language equivalent to:

> “Proceed only if you understand that this tool does not provide anonymity or confidentiality guarantees, does not prevent other participants from copying or redistributing content, and does not prevent harm if your device is compromised.
> If this is not acceptable, do not use the generated output.”

This is not consent theater; it is harm reduction.

### 7.8 Safety Language as a Change Gate

Any change that:
- Removes warnings
- Softens limitations
- Improves perceived safety without real protection
- Improves usability at the cost of clarity

...must be treated as a security regression.

### Outcome (Threat Model Complete)

At this point, threat-model.md:
- Defines the problem precisely
- States non-goals explicitly
- Enumerates attacker models
- Draws ethical risk boundaries
- Constrains design scope
- Anticipates failure
- Speaks honestly to users

This document now serves as:
- A design constraint
- A review checklist
- A justification for saying “no”
- An ethical record of intent

## Step 8 — What Comes Next (Outside the Threat Model)

Only after this document exists should you consider:
- A minimal README derived from it
- A design or implementation draft
- A repo structure that enforces these constraints
- A contribution policy that references this threat model

If at any point implementation pressures you to weaken this language, the correct response is to stop and reassess.