"""`python3 -m hee_regen` -- the entry point hee-repo-refresh regen calls."""
import sys

from . import main

sys.exit(main(sys.argv[1:]))
