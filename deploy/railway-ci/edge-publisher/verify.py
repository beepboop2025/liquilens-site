"""Run only controller-pinned Python code over a root-owned data snapshot."""

import runpy
import sys

sys.path.insert(0, "/verification/scripts")
runpy.run_path("/verification/scripts/verify_catalog_edge.py", run_name="__main__")
