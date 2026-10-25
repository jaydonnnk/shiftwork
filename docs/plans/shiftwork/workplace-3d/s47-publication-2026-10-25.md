# S47 acceptance and publication, 2026-10-25 Asia/Singapore

The user accepted S47 and authorized publishing its branch and pushing main:
"Accept. S46 is still ongoing. But u can publish ur branch and push to main."

## Published packet

Thirteen focused commits, 73660dd through bad906b, contain the 37 reviewed S47
files. They separate approved design, HTML mockups, pure mappings, client
presentation, inherited browser checks, new browser proofs and evidence records.
No co-author footer was added. No credential file, raw store, cache or bytecode
was staged. The exact publication paths passed a credential-pattern scan.

The code packet was pushed atomically to origin/shiftwork/slice-47 and
origin/main. git ls-remote returned
bad906b23b82689924b6310c8ca3204e63c8b2b8 for both remote refs, and both local
branches had zero left/right divergence from their remote tracking refs.
These publication notices follow in a documentation-only commit on both refs.

Main fast-forwarded from fc0d21d32a21d23534943ebec9bb2518126e8413. This also
lands the 17 already-accepted S45 commits through the S47 base
087585ff690194e6fde5d67be9827d732474879e. Main was not checked out in an active
worktree. Its ref was advanced with an expected-old-value check to the exact
tested S47 tree, without switching the primary, S46 or S47 checkout.

## Verification

- Fresh publication regression: Node 331 passed, zero failures. Python 1,732
  passed, one live-only skip, one explicitly deselected installation test and
  two known deprecation warnings. Both processes exited zero before commits.
- The accepted 222 final-byte browser rows remain valid: fullscreen 192,
  affected-fullscreen six and historical-ID 24. No browser or business journey
  was repeated for publication. All 18 client files match the accepted pin in
  both the working files and the committed Git blobs.
- All 106 protected fixture/sealed files, 44 inherited bytecode files including
  modification times, and 2,097 checked older receipt files are unchanged.
- The S47 index and worktree were clean after the code commits. git diff --check
  passed. The existing offline and device/AT/learning evidence limits remain.

Publication receipts: /tmp/shiftwork-s47-publication-20261025-a/.
commit-plan.json and commits.json retain the exact batches. node.log and
python.log retain fresh regression results. main-fast-forward.json,
push-code.log and code-publication-verified.json retain the initial publication.
Final metadata push and final remote checks are recorded separately in this root.

## S46 and stop boundary

S46 remains ongoing on its own branch and worktree. No S46 changes were merged,
no S46 process was started or stopped, and no S46 working file was edited.
The primary checkout stays on its prior S45 branch. The S47 worktree, existing
previews, protected files and all receipt roots remain preserved.

No combined S46/S47 verification, live call, installation, deployment or S48
work follows from this publication. S47 is accepted and published, with its
bounded local evidence preserved.
