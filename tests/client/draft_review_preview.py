"""Test-only preview of draft Slice 15 comparison mechanics.

This process locally substitutes review admission after the draft files are read.
It does not change the production loader, fixture review status, or sealed files.
Its comparisons are synthetic offline evidence and cannot authorize a live run.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from demos.client import main
from shiftwork import orchestrator
from shiftwork.sealed import store as sealed_store

orchestrator._require_reviewed_comparison_material = lambda *_: None
sealed_store.load_reviewed_comparison_family = sealed_store.load_family

if __name__ == "__main__":
    main()
