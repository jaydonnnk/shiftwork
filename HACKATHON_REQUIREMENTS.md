# Nebius x NVIDIA Global AI Hackathon Requirements

**Checked:** 2026-09-11
**Submission form fields added:** 2026-09-17 (user-provided from the live Devpost
submission form; on any conflict the official rules prevail)
**Official rules:** <https://nebiusglobalaihackathon.devpost.com/rules>

If this file conflicts with the current official rules, the official rules prevail.

## Dates

- Submission period: August 26, 2026 at 9:00 AM Pacific Time through October 30,
  2026 at 10:00 AM Pacific Time.
- Judging period: December 1, 2026 at 9:00 AM Pacific Time through December 15,
  2026 at 12:00 PM Pacific Time.

## Entrant eligibility

- An individual entrant must be at least the age of majority where they reside.
- Eligible individuals may enter alone, as a team, or through an eligible organization.
- A team or organization must appoint an eligible individual as its authorized
  representative.
- Participation and receipt of a prize must be legal in the entrant's jurisdiction.
- Entrants must not fall within the exclusions in Section 3 of the official rules,
  including specified sanctioned or prohibited jurisdictions, promotion entities and
  related persons, judges and their employers, and conflicts of interest.
- A project must not have received financial or preferential development support from
  the Sponsor or Administrator before the end of the submission period.

## Entry requirements

- Register for the hackathon through its Devpost website.
- Complete every required field on the submission page during the submission period.
- Accept the official rules and the applicable developer-tool license agreements.

## Project requirements

- Create a working software application.
- The application must do at least one of the following:
  - make a runtime call to the Nebius Token Factory inference API; or
  - be deployed or run using Nebius AI Cloud compute through Serverless Jobs,
    Serverless Endpoints, or DevPods.
- Use at least one NVIDIA open-source model.
- Fit one of the four hackathon tracks.
- Run consistently on its intended platform and function as shown or described in the
  submission.
- Be newly created by the entrant, or have been significantly updated after the
  submission period began. A pre-existing project requires a written explanation of
  those updates.
- Use third-party SDKs, APIs, data, trademarks, music, and other assets only with the
  required authorization and in accordance with their terms and licenses.

## Track requirements

- **Coding and Agentic Engineering:** Build coding agents or developer tools that
  write, run, and test code in Token Factory Sandboxes.
- **Best Apps and Agents:** Build a useful app or agent powered by Nemotron models on
  Nebius through Token Factory.
- **Personal AI:** Build an always-on private assistant that keeps the user's data
  under their control, has persistent memory and reusable skills, accesses only the
  tools and information selected by the user, and carries out tasks across daily
  workflows.
- **Physical AI:** Build an embodied or edge agent that senses and acts in the real
  world and is powered by NVIDIA open-source models. Its demonstration video must
  contain at least one minute of the physical hardware or robot operating. If there is
  no physical hardware component, show the key application modules in action instead.

## Submission requirements

- Submit a project that satisfies the project requirements above.
- Provide a URL to a working demo, hosted application, or test build. This URL is not
  required for a Physical AI submission evaluated under the hardware-access rule.
- Provide a text description of the project's features and functionality.
- Provide a public GitHub, GitLab, or Bitbucket repository for judging and testing.
- Include in the repository:
  - all source code and assets required for the project to function;
  - an open-source license file that is visible at the top of the repository page; and
  - a README with clear setup and run instructions.
- Explain how the project uses NVIDIA Nemotron or another NVIDIA open-source model,
  where Token Factory accelerated the workflow, and which other Nebius tools or
  services it uses.
- Provide feedback on the Nebius Token Factory, Nebius AI Cloud, and NVIDIA tools,
  models, or technologies used.
- Identify the selected track.
- Submit all materials in English. If any material is not in English, include an
  English translation of the video, description, testing instructions, and other
  submitted material.

## Submission form fields (live Devpost form)

Source: user-provided 2026-09-17 from the live submission form; not independently
re-verified. Factual field list only.

- Submitter type, country, province/state; track selection; new-vs-existing project
  declaration.
- **Upload a File** field for judges and organizers (zip/pdf/other, 35 MB limit) —
  a delivery channel for a test build besides a repo release or hosted URL.
- **Model feedback questions** (require real usage evidence; answers must never be
  fabricated or rated without observed data): which Nemotron model(s) and how used;
  Nemotron quality 1–10; fine-tuned / prompt-engineered / out-of-box; comparison
  against other models; recommend 1–10; experience 1–10; improvements wanted.
- **Nebius capabilities question**: "e.g. GPU instance types, deployment setup, API
  access, scaling" — the GPU wording is illustrative; Token Factory API access is a
  legitimate answer and renting GPUs is not required.
- **Tavily question**: "Did you use Tavily in your project? To qualify: your project
  must make a functional, runtime call to the Tavily API as part of its solution."
  The approved design keeps Tavily in the offline curation pipeline, never in the
  app's runtime path (architecture S11; Gate 3 test 39); whether a shipped,
  operator-run curation CLI's live `discover()` call satisfies the qualification is
  an interpretation question. Decision of record: Gate 4 `04-slices.md` S11
  decision 5 — pursue the bonus via that shipped call, answer "yes" only after it
  actually ships, and let the Test 3 KEEP/DROP verdict govern the pitch.
- Builders & Brews IRL city award dropdown (optional).

## Demonstration video requirements

- The video must be less than three minutes long.
- It must show the project functioning on the device for which it was built.
- It must be uploaded to YouTube, be publicly visible, and be linked in the submission.
- It must not contain third-party trademarks, copyrighted music, or other protected
  material unless the entrant has permission to use it.
- Physical AI submissions must also satisfy the track-specific footage requirement
  above.

## Repository, ownership, and testing requirements

- The submission must be the entrant's original work, be solely owned by the entrant,
  and not violate another party's intellectual-property, privacy, publicity, contract,
  or other rights.
- Open-source components may be used if their licenses are followed and the submission
  enhances and builds on their features or functionality.
- Give judges access to the working project through a website, functioning demo, or
  test build. If it is private, include login credentials in the testing instructions.
- Keep the project available to the Sponsor, Administrator, and judges free of charge
  and without restriction until the judging period ends.
- Be prepared to provide physical access on request if the project depends on
  proprietary or third-party hardware that is not widely available.
- Multiple submissions by the same entrant must be unique and substantially different
  from one another.

## Judging

### Stage One: pass or fail

- The project must meet a baseline level of viability.
- It must genuinely fit the selected track rather than superficially rebrand an
  unrelated idea.
- It must reasonably apply the required hackathon APIs or SDKs.

### Stage Two: scored 1-5 on four equally weighted criteria

1. Technological Implementation — how effectively you use Nebius Token Factory /
   AI Cloud and the NVIDIA model
2. Design
3. Potential Impact
4. Quality of the Idea

### Push past the obvious

Judges love to see tracks pushed further than the basics:

- **Coding and Agentic Engineering:** a code-completion wrapper is a start; an
  agent that plans, writes, tests, and iterates on a real repo with minimal
  human input is where it gets interesting.
- **Best Apps and Agents:** a single API call demo works; a multi-step
  autonomous workflow that chains tools end to end stands out more.
- **Personal AI:** a chatbot with a system prompt is fine; an assistant that
  remembers context across sessions and takes real action on your behalf is
  what we're hoping to see.
- **Physical AI:** a scripted demo is table stakes; hardware reacting live to
  real-world input is where this track can really shine.
