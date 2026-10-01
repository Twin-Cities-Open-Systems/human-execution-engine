# Name pools: retired

These pools fed `hee-name`, which is **deprecated** (operator, 2026-10-01):
`hee-name -allocate` refuses unless `HEE_NAME_ALLOW_DEPRECATED=1`.

Name things for what they are and do: a short 1-3 word phrase plus a number,
such as `haproxy-1`, `nginx-3` or `shell-1`. Always number it, even the first
one, and never zero-pad. This is the interim rule until a naming standard
exists. See fleet-ops `pve/GUIDE.md`, "Deploy a new container", step 2.

The files stay so that `hee-name -list-pools`, `-list` and `-release` keep
working while existing allocations are wound down. Names already in service
are not renamed by this.
