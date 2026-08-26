# Setting up an unprivileged human user on a touchy-managed box

Real trigger (2026-08-21): rebuilding `spencer@kiosk.lab.tcos.us`
properly. Spencer's own explicit framing, worth stating exactly rather
than paraphrased: *"the spencer@kiosk.lab.tcos.us account is unpriv and
you are root admin super user. I am just a user."* This doc generalizes
that one real setup into a repeatable procedure for any human account
on any Unix-y box a `touchy`-class identity administers.

## The authority model, stated plainly

On a box where a machine identity holds real, ratified (or in-progress)
operational sovereignty (see
[`kiosk.touchy.machine-sovereignty.contract.v1.yaml`](https://github.com/Twin-Cities-Open-Systems/fleet-ops/pull/209)),
a human's own account on that same box is, by deliberate design,
**unprivileged by default** — not sudo, not admin, a regular user. The
machine identity grants **fine-grained** privileges (a specific `sudo`
rule, `doas` if more flexible for the case, a specific group) only when
it reasons a specific real task actually needs them — never blanket
admin access handed out up front "just in case."

This is not the human ceding real control. Spencer's own reasoning,
worth keeping attached to this doc rather than left implicit: *"what
gives me real control here is 'I control the electricity and other
periphs.'"* Software-level authority (root, sudo) nests inside physical
authority (power, hardware access, the ability to walk up and unplug
the box) — the OS-level hierarchy can be inverted precisely because the
physical one can't be, and it's always the human who holds that one.

## Procedure

### 1. Clean slate — don't patch a broken partial setup

Check for and fully remove any existing incomplete account rather than
trying to finish it in place (real example: a `spencer` account existed
with no home directory, bare `/bin/sh`, never logged in — classic
`useradd` without `-m`, evidence of the exact mistake this procedure
exists to prevent):

```bash
getent passwd <username>                    # does it exist, in what state?
sudo deluser --remove-home <username>        # clean removal, nothing preserved
getent passwd <username>; echo $?            # confirm gone (nonzero = gone)
```

### 2. Create fresh with `adduser`, not `useradd`

`adduser` is Debian's higher-level, interactive/scriptable wrapper —
home directory, `/etc/skel` population, shell, matching group, all
handled in one command. `useradd` is the low-level POSIX primitive that
needs every one of those spelled out explicitly (`-m` for the home dir
being the classic one people forget) and is easy to get subtly wrong
for a real human account. Use `adduser`:

```bash
sudo adduser --disabled-password --gecos "Full Name" <username>
```

`--disabled-password` locks password login — pair with SSH key auth
(below), not a typed password, as the actual login mechanism.

### 3. Verify the group membership is genuinely minimal

```bash
id <username>
```

Should show the account's own primary group plus whatever `adduser`'s
own defaults add (typically just `users`) — **not** `sudo`, **not**
`adm`, **not** any group that grants real system access. If the
account needs something specific later, grant that one thing when a
real task actually requires it, not preemptively.

### 4. Dogfood `dotfiles` for real shell config

Don't hand-write `.bashrc`/`.vimrc`/etc. — this org has a real repo for
exactly this
([`dotfiles`](https://github.com/Twin-Cities-Open-Systems/dotfiles)).
Use it:

```bash
sudo cp -r /path/to/dotfiles-checkout /home/<username>/dotfiles-src
sudo chown -R <username>:<username> /home/<username>/dotfiles-src
sudo -u <username> bash -c "cd /home/<username>/dotfiles-src && ./install-dotfiles.sh -a"
```

Real output from the 2026-08-21 run — `install-dotfiles.sh` correctly
handled the skel-copied files already present (renamed rather than
silently clobbered):

```
Installing new .vimrc
Found existing .bashrc -- appending RenamedByInstallDotfiles to the name.
Installing (replacement) new .bashrc
Found existing .profile -- appending RenamedByInstallDotfiles to the name.
Installing (replacement) new .profile
Found existing .bash_logout -- appending RenamedByInstallDotfiles to the name.
Installing (replacement) new .bash_logout
Installing new .tmux.conf
Installing .vim
Installing new .gitconfig
Installing .git_template
Installing new .inputrc
Installing new .screenrc
Installing new .pylintrc
```

### 5. SSH key auth, not password auth

Given `--disabled-password` from step 2, the account needs a real login
path:

```bash
sudo mkdir -p /home/<username>/.ssh
sudo chmod 700 /home/<username>/.ssh
# the human's real public key goes in authorized_keys -- get it from
# them directly, don't generate a keypair on their behalf and hand
# them the private half over a channel that isn't already trusted
sudo chown -R <username>:<username> /home/<username>/.ssh
```

Also worth checking `sshd_config` isn't silently running on defaults
when it should be explicit (`PasswordAuthentication no`,
`PubkeyAuthentication yes`) — a real gap found alongside this exact
setup, not yet closed as of this writing.

### 6. Granting a specific privilege later

When a real task genuinely needs elevated access, grant the narrowest
thing that satisfies it — a single `sudoers.d` rule scoped to one
command, a specific group, `doas` instead of `sudo` if its simpler
per-rule model fits better — not blanket `sudo` group membership.
Matches the same graduated/fine-grained-grant principle already
established for machine-identity contracts
([`fleet-ops#209`](https://github.com/Twin-Cities-Open-Systems/fleet-ops/pull/209)'s
review thread) — applied here to a human's own account on a
machine-administered box, not just agent-to-agent grants.
