# Branding identities: org work vs. your own

`hee exif brand` stamps an identity into an image. Which identity comes from
a branding card, and the default is the org's. That default is right for
anything TCOS made and wrong for anything you made as yourself.

Written 2026-09-06, after the operator asked to tag a personal 1991 photo
and the org card was the only one that existed.

## What the org card writes

`tcos-audit/policy/branding.card.v1.yaml`, reached through `$HEE_BRANDING`:

```
Publisher    Twin Cities Open Systems
Credit       Twin Cities Open Systems
Rights       Copyright (c) 2026 Twin Cities Open Systems - Operations, LLC
Identifier   urn:oid:1.3.6.1.4.1.66550        <- the org's IANA enterprise number
UsageTerms   GNU General Public License v3.0
```

On a company artifact that is exactly right. On a photo of you, it asserts
that a legal entity owns your private life, and whoever you send it to can
read all of it.

## Make a personal card

Copy `library/branding/personal.example.card.v1.yaml` somewhere personal --
your own directory or `~/.config/hee/`, **not an org repo**. Two fields are
required and the rest should be left out:

```yaml
apiVersion: hee/v1
kind: Card
metadata:
  name: personal-branding
  annotations:
    inuid: null
    inuid_null_reason: personal
spec:
  name:
    full: "Spencer Butler"
  copyright:
    notice: "© {year} Spencer Butler"
```

Leave out `credit`, `identifier` and `license`. Publisher falls back to your
own name, and a personal photo has no enterprise number and usually no
license to assert. `{year}` is filled at stamp time.

## Use it

```sh
hee exif brand --branding ~/.config/hee/personal.card.v1.yaml photo.jpg
```

The output names the identity, so a mix-up is visible without reading the
file back:

```
hee-exif brand: photo.jpg  [Spencer Butler  via /home/spencer/.config/hee/personal.card.v1.yaml]
```

## The part that will catch you: branding only adds

Every field is written; none is cleared. Re-branding with a different card
therefore leaves the previous identity in place. Measured on a real file: a
personal card changed `Publisher` and `Credit` to the person, while the
org's `Rights`, PEN `Identifier` and GPL `UsageTerms` all stayed. The photo
claimed both identities and still carried the company's enterprise number.

`--reset` clears the identity fields the new card does not define:

```sh
hee exif brand --branding ~/.config/hee/personal.card.v1.yaml --reset --force \
  --artist "Spencer Butler" --copyright "© 2026 Spencer Butler" photo.jpg
```

`--force` is needed as well because `Artist` and `Copyright` are never
overwritten silently -- that protection is what makes them worth trusting.
Verify with `exiftool -a photo.jpg | grep -ci "twin cities\|66550"`, which
should print `0`.

Without `--reset`, `brand` warns when it sees another identity on the file
rather than leaving you to find out later.

## Photos you are about to send someone

Branding is the wrong tool here. For a photo going to a person rather than a
publication, the job is removing metadata, not adding it.

```sh
exiftool -a -G1 -s -gps:all -serialnumber -ownername spencer_1991.jpg
exiftool -all= -tagsfromfile @ -Orientation -ICC_Profile -o for-send.jpg spencer_1991.jpg
```

Keep `Orientation` or phones display it rotated; keep `ICC_Profile` or the
colors shift. Check GPS first: a phone photo *of* a print carries the
coordinates of wherever you photographed it. Check the embedded thumbnail
too -- it is generated at capture and does not always match later edits, so
a crop you removed can still be sitting inside the file.

Keep two copies: a tagged one for your archive, a stripped one to send. They
want opposite things and one file cannot be both.

## Working on the share

Write to a copy, never in place. An in-place edit across the `nuc1-pool`
NFS mount can truncate the file before it fails, and a scanned photo has no
second original.
