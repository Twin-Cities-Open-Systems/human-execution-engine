# References

External work that describes the same mechanisms HEE uses, arrived at
independently. Cited because convergent design from unrelated authors is
evidence; a document agreeing with its own prompter is not.

## Hazard & Haapio, *Wise Contracts: Smart Contracts That Work For People And Machines* (2017)

James Hazard (CommonAccord) and Helena Haapio (University of Vaasa / Lexpert).
In Schweighofer et al. (eds.), *Trends and Communities of Legal Informatics,
Proceedings of IRIS 2017*, pp. 425--432. SSRN 2925871.
Local copy: `/mnt/nuc1-pool/storage/docs/shared/ssrn-2925871.pdf`.

Describes, nine years before this repository, four of HEE's core mechanisms:

- **Hash-bound references** (§2.6): *"If that reference is made using a hash of
  the referenced record (and all the links in the supporting object are also
  based on hashes) then there is a one-way inclusion of the full context... the
  record itself is reduced to merely the essentials and an opaque hash, while
  the full context can be proved by the parties."* This is the `inuid` and
  SOA-anchor design, and the reason a recorded hash that does not reproduce
  from its seed is a defect rather than a cosmetic error.
- **Static records as nouns, decision-makers as verbs** (§2.9): *"Prose objects
  are static; they do not reason; they are nouns, not verbs. But these
  unintelligent prose objects provide anchors for many forms of intelligence."*
  This is the inventory / orchestra-leader / dispatcher split.
- **Git as the transmission medium** (§2.4): named explicitly as the medium
  for *"the 'legal' part of legal codification."* HEE's contracts-in-git, and
  the reason dispatch is git rather than a message queue.
- **Prototype inheritance of typed records** (§2.1): *"legal templates can be
  reduced to their constituent parts and assembled into desired forms very
  simply, as building blocks."* The HEE-MIB / TCOS-MIB split: a base module
  publishes types, downstream modules import and instantiate.

Where it does not map: their contracts bind legal parties across
jurisdictions and carry a localization layer; HEE's are authority grants
inside one organization. Cite the mechanism, not the scope.

## Grigg, *The Ricardian Contract* (2004) -- the direct precedent

Ian Grigg. https://iang.org/papers/ricardian_contract.html. Fetched in full,
2026-09-06.

Twenty years before this repository, defines the instrument as *"a single
document that is a) a contract offered by an issuer to holders... c) easily
readable by people, d) readable by programs (parsable like a database), e)
digitally signed, f) carries the keys and server information, and g) allied
with a unique and secure identifier."* That identifier is *"a canonical
message digest over the clearsigned document... included in all records of
transactions, and provides a secure (unforgeable) link from the document to
the accounting."* Signing: *"the Issuer signs the document in the OpenPGP
cleartext form with his contract signing key."*

Name-value pairs in a text file, OpenPGP signature, hash-as-identity carried
into every downstream record. That is a HEE Contract with an `inuid`.

**One real difference, and it should be a stated decision, not an accident:**
Grigg hashes the *clearsigned document*, so identity binds to a specific
signing event. HEE hashes a *declared seed*, so identity survives re-signing.
Both are defensible. HEE has never written down which it chose or why.

## CommonAccord / Cmacc-Org -- working prior art for prototype inheritance

James Hazard et al. https://www.commonaccord.org/ and
https://github.com/CommonAccord/Cmacc-Org. Fetched: site, issue #18 (the
abstract model), README, and real prose-object files under `Doc/G/`.

The model, in Hazard's words from issue #18: *"three levels of expansion...
{variablename} in a value, expanded by matching a key name in a dictionary.
[filename] in a dictionary, expanded by matching the name of another
dictionary... files in folders as the canonical form of dictionary since
they are widely used and understood, and the format of git."* Inheritance
is namespace-scoped: *"if the key is not blank, then the keys in the linked
dictionary will be treated as prefixed by the key... if no match is found,
treated by removing the prefix."*

A real instance: `P1.=[G/U/Who/acme_incorporated.md]` then
`EffectiveDate.YMD=2016-07-09` -- import a party object under a prefix,
override a field. That is the HEE-MIB / TCOS-MIB import, in markdown.

**Where HEE is stronger:** Cmacc links by *name only*. A `=[path]` reference
resolves to whatever is at that path today; the referenced object can change
underneath you. The `inuid` is precisely what Cmacc lacks.

**Where Cmacc is stronger:** prefix-scoped inheritance with fallback
de-prefixing, and "magic folders" -- computed defaults overridden by real
files. HEE's imports have no namespace rule and no computed-default concept.

## Clack, Bakshi & Braine, *Smart Contract Templates: essential requirements and design options* (2016)

arXiv 1612.04496. Fetched as PDF. The "SCT Paper" that Hazard & Haapio
extend. Four essential requirements -- create/edit, standard formats for
storage/retrieval/transmission, execution protocols with or without
signatures, and binding agreement to code -- map onto YAML authoring, git,
GPG ratification and `inuid` respectively. On binding: *"A candidate solution
for the requirements of an operational-level unique agreement identifier is
a cryptographic hash of the smart legal agreement... this is the technique
used in Ricardian Contracts."*

Names Monax's *dual integration*, which *"additionally provides a reverse
link."* HEE records forward hash references only; whether a referenced
object should know its dependents is an open question.

## Creative Commons three-layer license design -- the readability model

Legal code (lawyer-readable, operative) / commons deed (human-readable) /
machine-readable metadata. The discipline worth borrowing is explicit: **only
one layer is operative; the others are derived and never authoritative.**
HEE's equivalent is YAML as canonical, with web, man and gopher renderings
for humans and SNMP OIDs for machines -- and the same rule should be stated.

## Consulted and not cited

Lessig, *Code Is Law* (2000) -- framing only, no mechanism. De Filippi &
Hassan (2016) -- useful argument that rules cannot anticipate everything, so
deciding roles stay human; one sentence at most. Sztorc's "wise contracts"
(2017) -- a blockchain composability point unrelated to Hazard & Haapio's
usage. Hart & Moore (1988) -- incomplete contracts; motivates a dispatcher
over a policy engine, not chased in full.
