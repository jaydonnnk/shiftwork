# Role-scope research: GTM Engineer and Forward Deployed Engineer

**Date:** 2026-09-30.
**Status:** research input for the pending three-board scope revision
(`shiftwork_three_boards.md`). Not a gate approval, product claim or
learning-impact evidence.

**Method and caveats:** fetched by two research agents on 2026-09-30. Several
postings were read through third-party mirrors rather than the employer's own
applicant tracking system; those rows say "(mirror)". Postings are ephemeral.
Vendor blogs mix marketing with duties; where a claim rests on vendor material it
is labelled. Quoted numbers are as the cited source states them, not
independently verified.

## GTM Engineer (go-to-market engineer)

Role in one line: a builder inside go-to-market who builds and operates the data
and automation systems that generate pipeline, usually embedded with revenue
operations. Clay's framing: "GTM engineers build revenue engines using AI and
automation." The origin story is contested (Clay credits 2023; an earlier Scale AI
claim is unverified), and much public writing is vendor marketing.

| Company | What the posting says (abridged) |
| --- | --- |
| Marqeta, GTM Engineer | In Marketing Ops. "Architect enrichment, scoring, and signal pipelines, then extend them with AI tooling." Clay, Apollo, Marketo, Salesforce, Demandbase, Gong. APIs, webhooks, JS/Python/JSON. QA for data quality and deliverability. 4+ yrs. $108.2K to $135.2K. |
| Sierra, GTM Engineer (mirror) | "Own our enrichment infrastructure end-to-end." Builds AI agents and internal tools; "ship production code with PR review, observability, and proper error handling." Python, TypeScript, SQL/warehouse, Salesforce, HubSpot, Outreach, Clay, ZoomInfo, Cognism, Postgres, Fivetran. "Production experience with LLMs: prompt design, eval loops, error handling." 3+ yrs. |
| Baseten, GTM Engineer (posting plus mirror) | Revenue Operations, New York, $175K to $200K + equity. "Audit Baseten's GTM stack and ship AI-powered workflows"; own CRM enrichment and Clay orchestration. |
| LeanTaaS, Associate GTM Engineer (mirror) | 0 to 2 yrs. Pipelines for analytics, legal and commissions; integrate CRM, billing and finance via APIs; "automate lead enrichment, data hygiene"; version control, testing, error handling, monitoring; runbooks; daily AI coding tools. |
| Vercel, GTM Engineer (mirror) | A different flavor: "Ship code daily", 4+ yrs full-stack, AI models and APIs. Reads like product engineering with a GTM label. |

Workflow seen across sources: signal detection (funding, hiring, tech-stack
changes), enrichment waterfall, scoring and qualification, routing to an owner or
team, CRM hygiene and dedupe, outbound orchestration or human handoff,
measurement of pipeline outcomes. Tools named: Clay, Salesforce, HubSpot,
Marketo, Apollo, ZoomInfo, Cognism, Demandbase, Gong, warehouse SQL, REST APIs
and webhooks.

Where AI sits: deterministic logic owns triggers, suppression, dedupe, field
mapping and routing; LLMs own subjective work such as classification, research
summaries and personalization; larger deals keep human review. Practitioner
guidance warns against running expensive AI on every low-priority record.

What breaks (cited): routing errors, including leads "created without an owner,
queue, or team" and overlapping rules overwriting assignments (Pedowitz Group).
HubSpot's own documentation lists seven CRM sync error classes: associations,
custom code, duplicates, permissions, picklists, property mappings and property
values. Enrichment mistakes include unvalidated catch-all addresses, raw JSON
pushed into CRM fields, no dedupe, and stale manual CSVs (vanderbuild.co). No
public write-up of an LLM-hallucinated B2B enrichment incident was found; that
gap is recorded rather than filled.

Junior entry: the LeanTaaS 0 to 2 year posting is the clearest evidence, and its
first tasks are enrichment and hygiene automation, troubleshooting pipeline
failures, and runbooks. Note: OpenAI lists an "Applied AI Software Engineer, GTM
Growth Engineering" posting; the page returned 403 to the fetch and its contents
are not included.

## Forward Deployed Engineer

Role in one line: a customer-facing software engineer who embeds with one
customer, scopes an ambiguous problem into working software, and owns delivery
from first prototype to stable production inside the customer's systems.
Popularized by Palantir ("one customer, many capabilities"), now hired by
OpenAI, Anthropic, Scale AI, AWS, Microsoft and Google Cloud.

| Company | What the posting says (abridged) |
| --- | --- |
| Palantir, FDSE (Delta) and New Grad | 1+ yrs or new-grad entry. "Wrangling massive-scale data"; "developing custom applications tailored to customer needs"; engaging stakeholders from technical teams to executives; "driving projects from ideation to deployment"; up to 25% travel. New Grad: "custom applications, LLM workflows, and production solutions engineered for a specific customer's reality." |
| OpenAI, FDE (UAE) | "Own technical delivery across multiple deployments from first prototype to stable production." Scope work, sequence delivery, remove blockers, "codify working patterns into tools, playbooks, or building blocks." |
| Anthropic, FDE | Build production apps with Claude "within customer systems"; deliver "MCP servers, sub-agents, and agent skills"; white-glove deployment; ~25% travel. |
| Scale AI, FDSE (Public Sector) | Embed with government customers, "scope the problem, and turn it into working software"; own design, build, deploy and maintain; "data integrations that connect customer environments to Scale's platform and back." |

Lifecycle (partly synthesized from the postings above): discovery and problem
scoping, solution architecture with customer engineers, integration build
(full-stack apps, LLM workflows, agents), evaluation against the customer's
success criteria, staged rollout and adoption, and codifying repeatable patterns
back into the product. One honest gap: a formal handoff-to-support stage did not
appear in the fetched postings; they name "maintain" (Scale) and long-term
ownership (Anthropic) instead.

Versus adjacent roles: an analysis of 1,000 FDE postings (bloomberry.com, vendor
blog) reports no sales quotas and coding mandatory (Python in 66%); solutions
architects trend toward reference designs and pre-sales validation; consultants
deliver slideware while FDEs deliver maintained software.

What breaks (cited): adoption failure at scale (the widely cited MIT NANDA report
states 95% of generative AI pilots fail, via Fortune; contested, attributed).
Rollback of deployed customer-facing agents (a Sinch vendor survey of 2,500+
decision-makers reports 74%, via The Register, 2026-05). Legal liability from a
deployed chatbot (Air Canada, The Guardian, 2024-02). "Gravel road" custom code
that never standardizes (fde.academy, third-party). Blocked data access and
permissions (origin story, third-party).

Junior entry: Palantir's New Grad FDE posting requires no professional
experience, so a junior on-deployment framing is realistic.

## Sources

GTM: [Clay](https://www.clay.com/blog/gtm-engineering),
[Business Insider on Anthropic GTM AI role](https://www.businessinsider.com/anthropic-engineer-role-ai-sales-hiring-2026-9),
[Marqeta posting](https://www.marqeta.com/careers/54266b1f-83c0-45d5-9e7e-088a969586c1),
[Sierra posting (mirror)](https://simplify.jobs/p/7d368fe1-f703-4e9d-878e-e702876e2a20/GTM-Engineer),
[Baseten posting](https://jobs.ashbyhq.com/baseten) plus [mirror](https://brandengineering.ai/jobs/baseten-gtm-engineer-2026-05-25),
[LeanTaaS posting (mirror)](https://www.remoterocketship.com/company/leantaas/jobs/associate-gtm-engineer-united-states-remote),
[Vercel posting (mirror)](https://jobs.accel.com/companies/vercel/jobs/54058035-gtm-engineer),
[HubSpot sync error classes](https://knowledge.hubspot.com/salesforce/resolve-salesforce-integration-sync-errors),
[Pedowitz Group on routing recovery](https://www.pedowitzgroup.com/how-do-you-recover-leads-lost-to-routing-errors),
[vanderbuild on Clay mistakes](https://www.vanderbuild.co/blog/top-10-mistakes-in-clay-setup-fixes-included),
[The Signal FAQ](https://www.thesignal.club/p/26-faqs-about-gtm-engineering-in),
[reachly guide](https://www.reachly.co/blogs/what-is-gtm-engineering-the-complete-2026-guide-from-a-clay-certified-agency).

FDE: [Wikipedia](https://en.wikipedia.org/wiki/Forward_deployed_engineer),
[Palantir FDSE Delta](https://jobs.lever.co/palantir/dab396d4-2f14-4796-aac0-0d82883dccf0),
[Palantir New Grad](https://jobs.lever.co/palantir/2e6b0ac8-83e9-4be5-a3aa-cf319f751728),
[OpenAI FDE UAE](https://jobs.ashbyhq.com/openai/e9d435e1-1b9e-4715-84ce-75f372e5559c),
[Anthropic FDE](http://job-boards.greenhouse.io/anthropic/jobs/5302966008),
[Scale AI FDSE](https://scale.com/careers/4481921005),
[Latent Space interview](https://www.latent.space/p/forward-deployed-engineers-aiewf),
[Bloomberry analysis](https://bloomberry.com/blog/i-analyzed-1000-forward-deployed-engineer-jobs-what-i-learned/),
[fde.academy origin story](https://fde.academy/blog/how-palantir-invented-the-forward-deployed-engineer-model),
[Fortune on the MIT report](https://fortune.com/2025/08/18/mit-report-95-percent-generative-ai-pilots-at-companies-failing-cfo/),
[The Register on rollbacks](https://www.theregister.com/ai-ml/2026/05/13/ai-customer-service-bots-get-rolled-back-at-74-of-firms/5239800),
[The Guardian on Air Canada](https://www.theguardian.com/world/2024/feb/16/air-canada-chatbot-lawsuit).
