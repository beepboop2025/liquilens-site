"""Load the immutable controller without source-controlled import paths."""

import sys

sys.path.insert(0, "/controller")
from publish import main

main()
