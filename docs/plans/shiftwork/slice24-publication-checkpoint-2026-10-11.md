# S24 accepted and published

2026-10-11 Asia/Singapore. The user accepted S24 and authorized publication,
merge and push. The first atomic publication put main and shiftwork/slice-24 at
`d95c62dfdb69213a65b59c3333d445a33992cc6c`; both remote refs were verified. Local
main was fast-forwarded by fetch and never checked out in the workspace. This
checkpoint and its receipts are a metadata-only follow-up to that verified
publication.

Implementation, tests, documents and evidence were committed in 12 focused
batches; the fresh-checkout proof was a separate thirteenth commit. Each of the
619 scoped paths was committed with the blob id predicted in
publication-scope.json. The pushed source matches the fresh-tested source
exactly: after the fresh test only MISTAKES.md and the fresh-clone receipts
changed.

Fresh Windows clone at `C:\s24fresh` (core.autocrlf=true), existing Python
environment, no installation: 1,399 passed, 1 live-only skip, 2 warnings, exit 0.
Packaging was excluded. Both demos passed in the clone, with replay IDENTICAL and
reviewed-material digest `8d87c2dc...62d1fa`.

The first clone, at the 7-character `C:\s24f`, retained 2 failures, 1,397 passes
and 1 skip. Both failures are the host_path and slash_path scanner self-tests.
The scanner keeps only needles of at least 8 characters, so a 7-character working
directory is never treated as private. The rule (since `e1366d5`) and the test
predate S24. Failed receipts and the diagnosis are retained, and no source or
guard was changed to obtain the pass. Working directories shorter than 8
characters remain a portability limit.

Workspace preservation: no source, test or demo file changed during acceptance
and publication. The only changed files are .gitattributes, MISTAKES.md,
SHIFTWORK_PLAN.md, 00-status.md, the architecture review and the residual
checkpoint; every added file is the acceptance record or publication evidence.
The workspace stayed on shiftwork/slice-24 throughout.

Raw pytest receipts in the offline evidence keep 144 trailing-whitespace lines
from pytest output, as the committed S23 receipts do. The `-text` rule keeps
their bytes and recorded hashes exact.

Evidence: `evidence/slice24-publication-2026-10-11/`, holding the authorization,
publication scope, final-round receipts bundle, both fresh-clone receipt sets
with the path diagnosis, first-publication.json and final-preservation.json.

S24 acceptance is limited to trusted-local/offline behavior. It was accepted
without another independent review of the F1 to F6 repairs. Carried: untyped
readers outside the five converted row types, and the repeated no-action sentence
on inherited reprocessing. No model-quality, real CRM action, learner gain,
monetary cost or production readiness follows. S25, live calls, installations
and spending remain unauthorized.
