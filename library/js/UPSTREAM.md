# library/js/UPSTREAM.md -- vendored third-party code in this directory

Everything else in `library/js/` is ours. This file records the code that is
not, the same way `library/rrr/upstream/` records its vendored specimens: the
project, the exact version, the commit, the URL it came from, the hash of the
bytes actually checked in, and the license they arrive under.

**Why vendored at all.** These pages are served by busybox httpd out of a
directory. There is no bundler, no `node_modules` and no CDN reachable from the
lab, so a dependency is either a file in this directory or it does not exist.
A CDN `<script src>` would also be a third party able to run code on a page
that holds an owner token, which is not a trade this org makes.

## jsQR

| | |
| --- | --- |
| Vendored as | `library/js/qr-jsqr.js` |
| License file | `library/js/qr-jsqr.LICENSE.txt` |
| Project | jsQR -- a pure JavaScript QR code reading library |
| Upstream | https://github.com/cozmo/jsQR |
| Version | 1.4.0 |
| Upstream commit | `49a9633931fb8030ac2fc9cecc121d6e5a19f9a3` (`gitHead` of the published package) |
| Source of the bytes | `https://registry.npmjs.org/jsqr/-/jsqr-1.4.0.tgz`, member `package/dist/jsQR.js` |
| License | Apache-2.0 (`package.json`'s `license`, and the project's `LICENSE`, checked in verbatim beside the code) |
| Runtime dependencies | none |
| Authors | Cosmo Wolfe, Jefff Nelson |

### The bytes, and how to check them

```
sha256  bc40c8a15196236b2314db0856f72ca0b49980cd5413b8c852a7349f5fee0859   library/js/qr-jsqr.js
sha256  b5299b37917a1fe7a8cab9dd5cc6b8accf82663add80abe5bf7761a921cc6602   jsqr-1.4.0.tgz
sha512  dxLob7q65Xg2DvstYkRpkYtmKm2sPJ9oFhrhmudT1dZvNFFTlroai3AWSpLey/w5vMcLBXRgOJsbXpdN9HzU/A==   jsqr-1.4.0.tgz (npm `dist.integrity`, base64)
```

`qr-jsqr.js` is **byte-identical** to the published `dist/jsQR.js`; only the
filename differs, so that it sorts next to `qr.js` and so that a flat
`library/js/*.js` copy (which is how `fleet-ops/tools/store/web/build.sh`
consumes this directory) picks it up. Nothing in it was edited -- not a
comment, not a banner. That is deliberate: an edited vendor file cannot be
compared against upstream, and a hash that has to be explained is not
evidence.

Re-vendoring, or checking that what is here is what upstream published:

```sh
curl -sSL https://registry.npmjs.org/jsqr/-/jsqr-1.4.0.tgz -o /tmp/jsqr.tgz
tar xzf /tmp/jsqr.tgz -C /tmp
cmp /tmp/package/dist/jsQR.js library/js/qr-jsqr.js && echo identical
cmp /tmp/package/LICENSE      library/js/qr-jsqr.LICENSE.txt && echo identical
```

Measured 2026-09-19: the jsDelivr copy
(`https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js`) is byte-identical to
the npm tarball member, so either source gives the same file. The tarball is
the one recorded here because it is the one that also carries the license.

### What it is, mechanically

A webpack UMD bundle of the project's TypeScript, 10101 lines, no `eval`, no
network access, no DOM access, and no non-ASCII bytes. It exports one global,
`jsQR`, with the signature

```
jsQR(Uint8ClampedArray data, int width, int height, [options]) -> {binaryData, data, chunks, version, location} | null
```

It takes raw RGBA pixels and nothing else. Getting pixels out of a camera, a
canvas or a file is the caller's problem -- which is what `library/js/qr.js`
is for. Call `qr.js`, not this, so that the day this is replaced the callers
do not have to change.

### Why this project

It is one file, has no runtime dependencies, decodes from an `ImageData`
without a worker or a wasm blob to fetch, and is Apache-2.0. Anything that
replaces it has to clear the same bar; `qr.js` exists so that replacing it is
a one-file change.
