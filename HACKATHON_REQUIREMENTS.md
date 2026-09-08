# Nebius x NVIDIA Global AI Hackathon — Requirements Reference

**Checked:** 2026-09-08  
**Authoritative source:** <https://nebiusglobalaihackathon.devpost.com/rules>

If this file conflicts with Devpost, the current official rules prevail.

## Dates

- Submission deadline: 2026-10-30 at 10:00 AM Pacific Time.
- Judging: 2026-12-01 through 2026-12-15.
- The working project must remain available to judges free of charge and without
  restriction through judging.

## Hard project requirements

- Create a working software application.
- The application must either:
  - make a runtime call to the Nebius Token Factory inference API; or
  - be deployed/run using Nebius AI Cloud compute identified by the rules as
    Serverless Jobs, Serverless Endpoints, or DevPods.
- Use at least one NVIDIA open-source model.
- Fit one of the four tracks.

Celeste uses the first path: a live NVIDIA Nemotron call through Token Factory. Nebius
AI Cloud is not required for eligibility.

## Personal AI track

The product should be an always-on private assistant that:

- Keeps the user's data under their control.
- Has persistent memory.
- Has reusable skills.
- Accesses only tools and information chosen by the user.
- Carries out tasks across daily workflows.
- Uses at least one NVIDIA open-source model.

NemoClaw, OpenShell, Hermes Agent, and Nebius Serverless are examples introduced by
`such as`; they are not individually mandatory.

## Submission package

- Working project and working demo/test-build URL.
- Public repository containing all required source and assets.
- Visible open-source license and clear setup/run instructions.
- Public YouTube video, no longer than three minutes, showing the project functioning
  on its intended device.
- Description of what was built, why, and how it works.
- Named track.
- Explanation of NVIDIA model use, Token Factory acceleration, and other Nebius tools
  actually used.
- Constructive feedback on the relevant Nebius and NVIDIA tools.
- Significant-update explanation if the project predates the submission period.
- Authorized use of every third-party SDK, API, data source, trademark, and asset.

## Judging gates

### Stage One — pass/fail

The project must be viable, genuinely fit the selected track, and reasonably apply the
required APIs/SDKs. A superficial model call or rebrand can fail here even if it is
technically connected.

### Stage Two — equally weighted

1. Technological Implementation
2. Design
3. Potential Impact
4. Quality of the Idea

For Celeste, the submission must visibly connect the privacy gate, persistent local
memory, reusable skills, an approved tool action, and live Token Factory/Nemotron
inference into one coherent Personal AI workflow.
