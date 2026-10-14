"""Operator-only curation boundary (program design S3.8).

This package is an operator CLI surface. It is never imported by the runtime
application (``shiftwork/app.py`` and every module it reaches), it does not
answer customer requests, it cannot load protected assessment and it cannot
decide pass or fail. The runtime import isolation is enforced by
``tests/curation/test_ablation.py`` in both directions: a static scan of every
runtime module and a subprocess import probe.
"""
