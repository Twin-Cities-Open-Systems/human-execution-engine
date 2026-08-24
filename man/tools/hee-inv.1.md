# hee-inv(1)

hee-inv — inventory tool (v1.1)
Contract: hee/contracts/inventory.contract.v1.md

Subcommands:
  ingest <incoming_dir> [--tcos-repo <path>]
  unknown report [--tcos-repo <path>] [--warn-days N] [--crit-days N]

Principles:
- canonical truth is YAML in git
- evidence is content-addressed (sha256)
- write XMP sidecar (.xmp) pointers; attempt embedded XMP if supported (best-effort)
- fail closed if SOA anchor missing or repo invariants missing

Zip support:
- zip is preserved as evidence
- extracted files are ingested as individual evidence objects
- created objects record archive provenance via spec.source.archive_ref

Junk ignore:
- macOS junk: __MACOSX, .DS_Store, Thumbs.db, .AppleDouble, dotfiles
- Windows ADS junk: *:Zone.Identifier, *:OECustomProperty

*(no --help/-h output -- generated from the script's own header comment)*
