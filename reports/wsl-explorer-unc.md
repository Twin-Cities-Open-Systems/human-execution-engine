# WSL → Windows Explorer paths (UNC)

Paste these into **Windows Explorer** to browse Linux files and drag/drop into ChatGPT.

## Preferred

- `\\wsl.localhost\<DistroName>\home\<user>\...`

## Alternate

- `\\wsl$\<DistroName>\home\<user>\...`

## Helper

- `hee pathwin /home/<user>/.hee`
- `hee pathwin --dir /home/<user>/.hee/evidence/.../file.txt`

Notes:
- Under WSL, `<DistroName>` is usually `$WSL_DISTRO_NAME` (ex: `Ubuntu`).
