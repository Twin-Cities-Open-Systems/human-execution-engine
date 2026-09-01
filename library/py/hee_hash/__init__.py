"""hee_hash -- HEE's hash-chain primitive: legs -> duoples -> a stool root.

The names below are the package's public surface; they are imported here so
callers write `from hee_hash import SoaHasher` rather than reaching into the
submodule. __all__ states that intent, which is also what stops a linter
reading a deliberate re-export as an unused import (F401).
"""

from .soa import SoaHasher, verify_current_host

__all__ = ["SoaHasher", "verify_current_host"]
