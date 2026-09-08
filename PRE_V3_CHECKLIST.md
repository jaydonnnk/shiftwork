# Celeste v3 — Pre-Software-Factory Checklist

**Status:** Product boundary finalized on 2026-09-08. Software Factory gates have not started.

This is the sole durable handoff from the exploration phase into the v3 Software
Factory process. It records requirements, accepted architecture boundaries, measured
Windows behavior, and the remaining decisions. Old plans and session handoffs are not
authoritative.

## 1. Hackathon acceptance conditions

Source of truth: <https://nebiusglobalaihackathon.devpost.com/rules>

Celeste must:

- Be a working software application.
- Make a real runtime call to the Nebius Token Factory inference API **or** run on
  enumerated Nebius AI Cloud compute.
- Use at least one NVIDIA open-source model.
- Genuinely fit the Personal AI track.
- Be installable and run consistently as shown in the video and description.
- Provide a working demo or test build, a public repository, a visible open-source
  license, setup instructions, a public video of at most three minutes, and feedback.
- Remain available to judges free of charge and without restriction through the end of
  judging.
- Use authorized third-party SDKs, APIs, data, and assets.

### Binding interpretation for v3

- A live Token Factory inference call is Celeste's `runs on Nebius` prong.
- **Nebius AI Cloud is not required.** No AI Cloud VM, Serverless Job, Serverless
  Endpoint, or DevPod is part of the v3 core.
- The Personal AI track's list of NemoClaw, OpenShell, Hermes Agent, and Nebius
  Serverless is illustrative (`such as`), not a requirement to use each tool.
- Stage One still requires a genuine Personal AI product, not a superficial model call.
  Persistent memory, reusable skills, tool access, and real task execution must be
  visible in the working product.

## 2. Frozen v3 product boundary

### Product sentence

Celeste is a private, always-on Windows assistant that uses one user-authored policy to
control both pixel and accessibility-text perception before approved context reaches
any model, remembers work locally, and helps the user resume it through small,
user-approved actions.

### Core path

1. Observe foreground-window state locally.
2. Identify the window using process, title, URL metadata when available, and explicit
   user rules.
3. Apply the same fail-closed gate before **either** WGC pixel capture **or** UIA text
   reads.
4. Keep denied pixels and denied UIA text out of skills, memory, logs, and inference.
5. Reduce allowed observations to the minimum approved text/metadata locally.
6. Store persistent memory locally.
7. Invoke a reusable skill.
8. Make a live text inference call to an NVIDIA Nemotron model through Nebius Token
   Factory only when deterministic logic cannot complete the job.
9. Present a suggestion or a narrowly scoped action for explicit user approval.
10. Execute approved actions through a local allowlisted broker and record the result.

### Required Personal AI capabilities

- **Always-on:** foreground activity and observability state continue across normal
  daily work without continuous model calls.
- **Private:** raw denied content never reaches a model; allowed context is minimized
  before egress; all cloud boundaries are visible to the user.
- **Persistent memory:** work sessions, interruption outcomes, re-entry state, and user
  corrections survive application restarts in a local store.
- **Reusable skills:** at minimum `ReEntry` and `HonestyMirror` implement one common
  skill contract. Skills consume only gated observations and cannot open their own
  capture or UIA channel.
- **Tool access:** a local action broker exposes a small allowlist. Initial candidates
  are `focus_window`, `open_approved_resource`, and `start_focus_session`; Gate 2 will
  choose the final set.
- **Task execution:** the demo must show at least one approved action actually being
  performed, not merely recommended.

## 3. Retained technology choices

- **Client:** C# / .NET 8, WPF shell.
- **Windows integration:** Win32 foreground/window state, Windows.Graphics.Capture,
  native UI Automation COM APIs, Windows.Media.Ocr fallback.
- **Identity:** sparse MSIX package identity where Windows OCR requires it; an
  unpackaged degradation tier may omit OCR.
- **Rules:** deterministic parser. An LLM never interprets security policy.
- **Local persistence:** format and library deferred to Software Factory Gate 2; data
  remains local by default.
- **Inference:** an OpenAI-compatible Token Factory adapter behind an application-owned
  interface.
- **Models:** Nemotron 3 Nano for cheap gating/classification and Nemotron 3 Super for
  user-facing synthesis are preferred, not hard-coded assumptions.
- **Optional bonus integration:** Tavily resolves an unknown bare domain/process into a
  cited category. The query and result are disclosed and cached locally.

### Token Factory requirements

- At implementation time, query `GET /v1/models` with the project API key and record
  the exact working NVIDIA model IDs.
- Run and preserve a real inference receipt for each model used: timestamp, model ID,
  request ID if returned, token usage, latency, and a redacted request/response digest.
- Keep model IDs configurable so deprecation does not require an application rebuild.
- Never embed a Token Factory key in the Windows binary, browser code, repository,
  installer, logs, or screenshots.
- Local development may read a key from an ignored environment variable or user secret
  store. The judge-facing build must call a protected proxy funded by the entrant.
- The proxy provider is a Gate 2 decision. It need not run on Nebius AI Cloud.
- The proxy must enforce a total budget, per-client rate limits, request-size limits,
  model allowlists, and no application-level prompt retention.
- A canned replay is a labeled fallback only; it does not replace the required live
  Token Factory call in the working project.

## 4. Explicitly excluded from the v3 core

- Nebius AI Cloud compute.
- A Nebius VM kept alive for development or judging.
- NemoClaw/OpenShell as action-side enforcement.
- Claims that all of `celeste.rules` compiles into a second sandbox policy.
- A remote Linux agent that cannot naturally reach the local Windows context.
- A Serverless Job pretending to run a loop over local Windows activity.
- A browser demo that claims parity with native foreground-window enforcement.
- Any sponsor tool included only for name recognition.

NemoClaw/OpenShell may be reconsidered after the core submission works, but only as a
separately labeled experiment with a real end-to-end task. It cannot block or define
v3 and receives no budget by default.

## 5. Privacy and evidence claims

### Class A — never observed by Celeste

- A denied or unidentified window is rejected before creating a WGC capture item and
  before reading UIA text or name properties.
- Process/title/URL metadata used for identification is a separate, explicitly
  disclosed tier: metadata can leak information and titles can be spoofed.

### Class B — minimized before egress

- An allowed frame may enter Celeste's process.
- UIA selects the permitted region when available; everything else is removed locally.
- Only minimized, approved context can reach a skill, persistent memory, Tavily, or
  Token Factory.
- Class B is weaker than Class A because raw pixels briefly exist in Celeste's process.

### Ledger language

- The ledger records decisions, observation channel (`pixels`, `uia-text`,
  `uia-name`, or `metadata`), rule, observability state, egress destination, and hashes.
- A hash chain is **tamper-evident after the fact**. It does not independently prove
  that no unrecorded capture occurred.
- Publish the genesis hash with the submission evidence.
- Never claim `no frame hash in the ledger` proves that no hidden frame ever existed.

## 6. Measured Windows findings to carry into design

Measured on Windows 11 build 26200 during 2026-09-07/08:

- Windows OCR languages installed: en-GB, en-US, zh-Hans-CN.
- Developer Mode is enabled.
- .NET SDK 8.0.424 and Windows SDK 10.0.26100.0 are installed.
- A self-signed sparse package successfully attached identity and created an OCR
  engine. Package identity remains required for Windows.Media.Ocr.
- Border suppression worked in packaged and unpackaged probes on this machine. The
  reported consent status is not reliable proof that the border is absent.
- WGC is change-driven, not a heartbeat.
- Frames continued while a changing window was occluded.
- On minimize, a changing stream delivered zero frames and fired no `Closed` event.
- Creating a session for an already minimized window succeeded but reported an
  icon-sized item and delivered zero frames.
- Production must poll `IsIconic`, enter an explicit `NOT_OBSERVABLE` state, discard
  the retained frame, and refuse to serve stale data to any model or skill.
- UIA TextPattern worked for Word, Notepad, VS Code/Monaco, and Chromium's address bar.
- UIA `Sentence` expansion failed across tested providers; fetch paragraph/line text
  and segment sentences locally.
- Rich Chromium page caret text was unreliable; use a gated DocumentRange or OCR
  fallback.
- Tested Electron shells exposed no useful TextPattern; use a gated OCR fallback.
- UIA name properties can expose entire content bodies. UIA is an independent ingestion
  channel and must pass through the same policy gate as pixels.
- Production should use native UIA COM, not the old `System.Windows.Automation` managed
  wrapper used by the exploratory probe.

The untested border-consent-denied branch is **not a v3 gate**. The product must handle
all non-allowed/unknown statuses by degrading visibly and failing closed.

## 7. Demo and submission constraints

- The native Windows build is the primary working product and must be shown running on
  Windows in the video.
- The judge link may be a downloadable signed/test build plus clear installation and
  test instructions. A scoped browser explainer is optional and must not claim native
  parity.
- Use fictional windows, domains, documents, people, and data in screenshots and the
  video. Do not show real bank, messaging, password-manager, or personal records.
- Do not include third-party trademarks, copyrighted music, private data, API keys,
  certificate private keys, or captured desktop logs in public artifacts.
- Include a visible MIT license, README architecture diagram, privacy boundary,
  limitations, setup steps, model IDs, Token Factory evidence, and prior-existence
  statement.
- Test the exact judge path from a clean Windows account before submission and again
  before judging.
- Keep the live proxy funded and operational through 2026-12-15. Record credit expiry
  dates when promotional credits are actually claimed.

## 8. Remaining decisions for Software Factory

Do not implement v3 before all four Software Factory gates are approved.

### Gate 1 — Product

- [ ] Create `docs/plans/celeste-v3/00-status.md`.
- [ ] Define one target audience and one measurable success metric.
- [ ] Specify the onboarding, rule editor, re-entry card, approval prompt, and Mirror
  screens with plain HTML mockups.
- [ ] Approve the product behavior without architecture discussion.

### Gate 2 — Architecture

- [ ] Choose the local persistence format and retention/deletion controls.
- [ ] Define the single gate used by WGC, UIA, memory, skills, Tavily, and inference.
- [ ] Choose the judge proxy provider and secret-storage mechanism.
- [ ] Choose the exact initial action-broker allowlist and Windows APIs.
- [ ] Verify current Token Factory model IDs and capabilities against the live account.
- [ ] Decide whether Tavily remains in the core or is a post-core bonus slice.

### Gate 3 — Program design

- [ ] Define files, types, signatures, call stacks, threat boundaries, and failure
  states before implementation bodies exist.
- [ ] Define the reusable skill interface and prove skills cannot bypass the gate.
- [ ] Define ledger semantics and tests before writing the ledger.
- [ ] Define the clean-install, proxy-budget, privacy, and adversarial test cases.

### Gate 4 — Vertical slices

- [ ] Start with a visible end-to-end tracer bullet.
- [ ] Build the smallest real gated-observation → Token Factory → card path.
- [ ] Add persistent memory, one skill, and one approved tool action before expansion.
- [ ] Add privacy classes, ledger, second skill, Tavily, and submission polish as
  separate testable slices.

## 9. Cleanup boundary

Retain only:

- This checklist.
- The concise hackathon requirements reference.
- Reusable source and scripts from the Windows capture harness.
- Repository ignore rules.
- Future Software Factory documents and v3 source created after gate approval.

Remove old plans, backup copies, session-transfer documents, one-off work orders,
Devpost screenshots, captured logs, signing certificates, packaged binaries, build
outputs, stage folders, and the failed Probe 3 working copy. A pre-cleanup archive is
stored outside this project for recovery.
