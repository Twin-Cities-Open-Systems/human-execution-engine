% HEE-INV(1) | HEE Tools

# NAME

hee-inv - ingest inventory evidence, and report on what is unaccounted for

# SYNOPSIS

    hee inv ingest INCOMING_DIR [--tcos-repo PATH]
    hee inv add --json FILE [--dataset DIR | --tcos-repo PATH] [--kind asset|stock] [--dry-run]
    hee inv unknown report [--tcos-repo PATH] [--warn-days N] [--crit-days N]
    hee inv help


# DESCRIPTION


    ingest reads an incoming directory and files its contents as inventory
    evidence. A .zip is preserved AS the evidence and its contents are
    ingested alongside it -- the archive is not discarded once opened.

    unknown report ages the items that have not been reconciled, warning
    and then going critical as they get older.

    add renders one record from a JSON document -- FILE, or - for stdin --
    and prints the path it wrote. It is the same document the inventory
    page's add form submits. It refuses a document that breaks the contract
    and a record name that already exists. --dry-run prints the record and
    writes nothing.

    --dataset DIR writes into DIR/inventory/objects/<kind>/ instead of the
    tcos-plan-private repo: DIR must already exist as a directory, and is
    NOT required to be a git repository (a store's dataset directory on the
    share is not one). --dataset and --tcos-repo are mutually exclusive; the
    SOA anchor is still required either way.

    --kind asset (the default) takes schema hee.inventory.asset-request.v1,
    rendering one inventory.asset record. The allowed sub, bucket and
    lifecycle values are read from the contract.

      Document fields (name, asset_type, sub, bucket, lifecycle required):
        name, asset_type, sub, bucket, lifecycle, stableid, vendor, model,
        serial, interfaces [{role, mac}], location {path}, specs {},
        requirements [],
        refs [], notes, source {}, observed
      stableid, in order: as given; else the serial; else asset_type-TSZ.

    --kind stock takes schema hee.inventory.stock-request.v1, rendering one
    inventory.stock record in the same dataset as the asset it stocks --
    metadata.labels.inv.bucket and inv.sub are copied from that asset record,
    not re-entered. One stock record per asset: a second is refused like a
    duplicate asset record name is.

      Document fields (asset, qty, price, currency required):
        asset, qty, unit, price, currency, available, observed, notes
      asset MUST name an existing inv-asset-* record in the same dataset.
      qty is an integer >= 0. price is a decimal string with at most 2
      places and no sign. currency is three uppercase letters. unit is a
      token, default each. available is true or false, default true.

    Defaults:
      --tcos-repo   $HOME/git/tcos-plan-private
      --kind        asset
      --warn-days   7
      --crit-days   14


# EXIT STATUS

    Nagios plugin convention.
    0 OK   1 WARNING   2 CRITICAL   3 UNKNOWN
    add: 0 written, 2 invalid document or the name exists,
         3 usage, unreadable file, missing contract, dataset, repo or SOA anchor

# EXAMPLES

    $ hee inv add --json tests/fixtures/inv-dataset/stock-request.json --dataset tests/fixtures/inv-dataset --kind stock --dry-run   # ci
