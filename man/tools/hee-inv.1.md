% HEE-INV(1) | HEE Tools

# NAME

hee-inv - ingest inventory evidence, and report on what is unaccounted for

# SYNOPSIS

    hee inv ingest INCOMING_DIR [--tcos-repo PATH]
    hee inv add --json FILE [--tcos-repo PATH] [--dry-run]
    hee inv unknown report [--tcos-repo PATH] [--warn-days N] [--crit-days N]
    hee inv help


# DESCRIPTION


    ingest reads an incoming directory and files its contents as inventory
    evidence. A .zip is preserved AS the evidence and its contents are
    ingested alongside it -- the archive is not discarded once opened.

    unknown report ages the items that have not been reconciled, warning
    and then going critical as they get older.

    add renders one inventory.asset record from a JSON document -- FILE, or
    - for stdin -- of schema hee.inventory.asset-request.v1, and prints the
    path it wrote. It is the same document the inventory page's add form
    submits. The allowed sub, bucket and lifecycle values are read from the
    contract. It refuses a document that breaks the contract and a record
    name that already exists. --dry-run prints the record and writes nothing.

    Document fields (name, asset_type, sub, bucket, lifecycle required):
      name, asset_type, sub, bucket, lifecycle, stableid, vendor, model,
      serial, interfaces [{role, mac}], location {path}, requirements [],
      refs [], notes, source {}, observed
    stableid, in order: as given; else the serial; else asset_type-TSZ.

    Defaults:
      --tcos-repo   $HOME/git/tcos-plan-private
      --warn-days   7
      --crit-days   14


# EXIT STATUS

    Nagios plugin convention.
    0 OK   1 WARNING   2 CRITICAL   3 UNKNOWN
    add: 0 written, 2 invalid document or the name exists,
         3 usage, unreadable file, missing contract, repo or SOA anchor
