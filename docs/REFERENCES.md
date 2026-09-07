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
