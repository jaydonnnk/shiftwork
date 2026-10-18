# S28 implementation and deployment plan

Authority: Jaydon permits minimal startup and route wiring, fresh existing meters
per bounded action, hosted deployment/publication and pushing code to production.
The 2026-10-18 clarification reopens no gate. User-reported Render service:
https://shiftwork.onrender.com, main, Free/Hobby, no payment method; credentials
are in Render only. Credit expiry: none, user report. Verify external claims.

1. Add `shiftwork/hosted.py`. The existing app entry point delegates only when
   Render's documented `RENDER=true` flag is present and no explicit test/demo
   executor was supplied. Both credentials select tokenfactory; a missing one
   selects recorded fallback. Validate present credentials without exposing them.
   Verify all six Sandbox permissions during hosted startup, without a spawn or
   inference call. Supply LiveAssistGateway and fresh LiveOperationBudget and
   LiveComparisonBudget factories, preserving classes and ceilings unchanged.
2. App injection accepts either historical meter instances or typed factories.
   Routes resolve each factory once per bounded action and pass that instance
   through background execution. Comparison's existing atomic claim remains.
   Claim a queued selected operation atomically before execution so duplicate
   requests cannot create independent live allowances for the same run.
3. Expose a small runtime notice endpoint with mode, reset/sleep warning, Python
   version, sanitized preflight permissions and a per-boot marker. Render that
   notice in the existing vanilla client. Show the recorded fallback explicitly.
   Pin Python 3.13.12 using .python-version, without dependency/lockfile changes.
4. Write fail-capable offline tests before production edits. Prove every new
   branch with a separate assertion-level mutation on a disposable copy; restore
   target bytes exactly and rerun green. Exercise repeated actions, duplicate
   requests, wrong/missing pieces, key/project combinations and six permission
   failures, without any provider traffic or credential value in receipts.
5. Run the full suite and separate packaging test, retain the known port_dead
   and Northline mobile red rows. Review the whole change and architecture before
   publication. Commit by concern, no co-author trailers.
6. Record hosted state before publication. Push the branch and fast-forward main
   under the user's production-push authorization, then observe the actual deploy.
   Reproduce the fresh-database reset and startup/preflight, record bounded public
   polling and representative six-screen/browser checks against the public URL.
   Run one bounded model-backed action; diagnose before any retry. Record usage
   and latency, distinguish estimated inference cost from unknown Sandbox cost.
7. Update README, judge path and 00-status with actual evidence and limits. Keep
   the existing downloadable build available. Complete post-slice cleanup, then
   ask Accept S28, or re-steer? Leave incomplete items explicitly unknown.

Rates for meter projections retain the existing 0.06/0.24 USD per million
input/output constants. These are historical estimates, not a current verified
vendor price card. No guaranteed credit duration, funded availability, learner
outcome, production readiness or submission claim follows.
