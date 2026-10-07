# Public qualification and routing contract

## task.required_results

Qualification is required. Every active owner, pipeline-record or handoff task is mandatory even though the task is conditional. Return an explicit NOT_APPLICABLE result for each inactive task.

## gtm.qualification

Suppressed accounts and accounts below 50 employees are disqualified. A current confident RESEARCH interpretation is disqualified. Missing, stale or unavailable enrichment, unknown region/product, ambiguous intent or confidence below 80 requires human review. Current BUYING signals with explicit demo, pricing or security-review notes qualify. A current confident BUYING interpretation without those explicit phrases may qualify or enter human review. No fabricated fit fact is permitted.

## gtm.pinned_routing

Qualified signals use the frozen region/product owner map. REVIEW signals use revenue-review. DISQUALIFIED signals have no owner, record or handoff. The pinned task specification states the permitted qualification decisions and qualified owner independently of either workflow.

## gtm.exactly_once

One owner_assignment and one pipeline_write output per first processed signal. A retry must retain qualification and output NOT_APPLICABLE for owner, write and handoff, without another commitment. The assessor checks the earlier captured output or a frozen existing record. These are synthetic output records, not proof of a write to an external CRM.

## gtm.human_handoff

REVIEW requires one COMPLETED HANDOFF_TO_REVIEW to revenue-review. This is a record for a human queue, never a sent customer message. No send field or revenue quantity exists in the output grammar.

## response.structured_only

Only the task-aware envelope is accepted. No independent customer prose. Every active claim cites the exact frozen signal evidence. A pipeline row includes a bounded decision trace and a stable signal-bound record reference.

Routing map:

- APAC/platform: owner-apac-platform
- EMEA/platform: owner-emea-platform
- AMER/platform: owner-amer-platform
- APAC/analytics: owner-apac-analytics
- EMEA/analytics: owner-emea-analytics
- AMER/analytics: owner-amer-analytics
