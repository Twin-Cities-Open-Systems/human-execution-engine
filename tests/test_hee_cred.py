"""hee-cred: -genkey es256 seals a private key and prints a JWKS; -backend age seals and opens with an age identity;
-passphrase seals identity keys with age -p and -install-keys puts them where ssh and gpg look."""
import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tooling" / "bin" / "hee-cred"
CHECK_EC = 'printf "%s" "$HEE_CRED_PASS" | openssl ec -check -noout 2>&1'


class GenKey(unittest.TestCase):
    def test_genkey_seals_private_and_prints_public_jwks(self):
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, GNUPGHOME=d)
            subprocess.run(["gpg", "--batch", "--quick-gen-key", "--passphrase", "", "t@test", "ed25519", "cert,sign", "0"], env=env, check=True, capture_output=True)
            subprocess.run(["gpg", "--batch", "--quick-add-key", "--passphrase", "", subprocess.run(["gpg", "--list-keys", "--with-colons", "t@test"], env=env, capture_output=True, text=True).stdout.split("fpr:::::::::")[1].split(":")[0], "cv25519", "encr", "0"], env=env, check=True, capture_output=True)
            secrets = Path(d) / "s"
            r = subprocess.run([sys.executable, str(TOOL), "-seal", "issuer", "-recipients", "t@test", "-genkey", "es256", "-dir", str(secrets)], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((secrets / "issuer.gpg").exists())
            self.assertNotIn("BEGIN EC PRIVATE KEY", r.stdout + r.stderr)      # private half never printed
            jwks = json.loads(r.stdout[r.stdout.index("{"):])
            k = jwks["keys"][0]
            self.assertEqual((k["kty"], k["crv"], k["alg"]), ("EC", "P-256", "ES256")); self.assertEqual(len(k["kid"]), 16)
            # the sealed private key is a usable EC key
            r2 = subprocess.run([sys.executable, str(TOOL), "-pass", "issuer", "-dir", str(secrets), "-exec", "sh", "-c", CHECK_EC], env=env, capture_output=True, text=True)
            self.assertIn("EC Key valid", r2.stdout + r2.stderr)


def run_tool(*args, env=None):
    return subprocess.run([sys.executable, str(TOOL), *args], env=env, capture_output=True, text=True)


class AgeBackend(unittest.TestCase):
    """The TPM case needs a TPM; a plain X25519 age identity exercises the same code path."""

    @unittest.skipUnless(shutil.which("age") and shutil.which("age-keygen") and shutil.which("openssl"),
                         "needs age, age-keygen and openssl on PATH")
    def test_age_seal_then_open_with_identity_flag_and_env(self):
        with tempfile.TemporaryDirectory() as d:
            ident = Path(d) / "identity.txt"
            subprocess.run(["age-keygen", "-o", str(ident)], check=True, capture_output=True)
            recipient = subprocess.run(["age-keygen", "-y", str(ident)], check=True, capture_output=True, text=True).stdout.strip()
            secrets = Path(d) / "s"
            r = run_tool("-seal", "issuer", "-backend", "age", "-recipients", recipient, "-genkey", "es256", "-dir", str(secrets))
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((secrets / "issuer.age").exists())
            self.assertFalse((secrets / "issuer.gpg").exists())
            self.assertFalse((secrets / "issuer.age.tmp").exists())             # swapped into place, nothing left over
            self.assertIn("BEGIN AGE ENCRYPTED FILE", (secrets / "issuer.age").read_text())
            self.assertNotIn("BEGIN EC PRIVATE KEY", r.stdout + r.stderr)
            # -identity opens it
            r2 = run_tool("-pass", "issuer", "-dir", str(secrets), "-identity", str(ident), "-exec", "sh", "-c", CHECK_EC)
            self.assertIn("EC Key valid", r2.stdout + r2.stderr)
            # and so does HEE_CRED_AGE_IDENTITY, with -run's derived variable
            env = dict(os.environ, HEE_CRED_AGE_IDENTITY=str(ident))
            r3 = run_tool("-run", "issuer", "-dir", str(secrets), "-exec", "sh", "-c", 'test -n "$ISSUER"', env=env)
            self.assertEqual(r3.returncode, 0, r3.stdout + r3.stderr)

    def test_age_credential_without_identity_names_the_fix(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x.age").write_text("placeholder\n")
            env = {k: v for k, v in os.environ.items() if k != "HEE_CRED_AGE_IDENTITY"}
            r = run_tool("-pass", "x", "-dir", d, "-exec", "true", env=env)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("HEE_CRED_AGE_IDENTITY", r.stderr)

    def test_both_backends_for_one_account_refuses_to_guess(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x.gpg").write_text("placeholder\n")
            (Path(d) / "x.age").write_text("placeholder\n")
            r = run_tool("-pass", "x", "-dir", d, "-exec", "true")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("refusing to guess", r.stderr)

    def test_seal_refuses_a_second_backend_before_asking_for_a_secret(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x.gpg").write_text("placeholder\n")
            r = run_tool("-seal", "x", "-backend", "age", "-recipients", "age1placeholder", "-dir", d)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("one account, one backend", r.stderr)
            self.assertNotIn("interactive terminal", r.stderr)                  # refused before the secret prompt
            self.assertFalse((Path(d) / "x.age").exists())


FAKE_AGE = r'''#!/usr/bin/env python3
# A stand-in for age's passphrase mode. The real `age -p` asks for the
# passphrase on the controlling terminal, which a test run must not own; this
# one writes the same file shape (armored, an scrypt stanza in the header) so
# hee-cred's own detection, refusal and install logic is what gets tested.
import base64, sys
args = sys.argv[1:]
HDR = b"age-encryption.org/v1\n-> scrypt FAKESALT 18\nFAKEBODY\n--- FAKEMAC\n"
if "--encrypt" in args:
    if "-p" not in args or "-r" in args:
        sys.exit("fake age: expected -p and no -r")
    raw = HDR + sys.stdin.buffer.read()
    b64 = base64.b64encode(raw).decode()
    sys.stdout.write("-----BEGIN AGE ENCRYPTED FILE-----\n"
                     + "\n".join(b64[i:i + 64] for i in range(0, len(b64), 64))
                     + "\n-----END AGE ENCRYPTED FILE-----\n")
elif "--decrypt" in args:
    if "-i" in args:
        sys.exit("fake age: an identity was given for a passphrase-sealed file")
    data = open(args[-1], "rb").read()
    lines = [l.strip() for l in data.splitlines()[1:] if l.strip() and not l.startswith(b"-----")]
    sys.stdout.buffer.write(base64.b64decode(b"".join(lines)).split(b"--- FAKEMAC\n", 1)[1])
else:
    sys.exit("fake age: unexpected arguments")
'''
FAKE_HEE_TRUST = '#!/bin/sh\n[ "$1" = anchor ] || exit 9\nmkdir -p "$HOME/.hee/index" && printf \'id: "hee://_/index/_.yaml"\\n\' > "$HOME/.hee/index/_.yaml"\n'


class PassphraseBackend(unittest.TestCase):
    """-passphrase and -install-keys: the fake age above stands in for `age -p`;
    the refusal without a terminal is exercised against the real check."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bin = Path(self.tmp) / "bin"; self.bin.mkdir()
        (self.bin / "age").write_text(FAKE_AGE); (self.bin / "age").chmod(0o755)
        (self.bin / "hee-trust").write_text(FAKE_HEE_TRUST); (self.bin / "hee-trust").chmod(0o755)
        self.home = Path(self.tmp) / "home"; self.home.mkdir()
        self.secrets = Path(self.tmp) / "keys"
        # HEE_CRED_TTY=/dev/null: the fake age never prompts, so the terminal
        # check is satisfied by a path that always opens.
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ.get('PATH', '')}",
                        HOME=str(self.home), HEE_CRED_TTY="/dev/null")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def tool(self, *args, stdin=None, env=None):
        return subprocess.run([sys.executable, str(TOOL), *args], env=env or self.env,
                              stdin=stdin, capture_output=True, text=True)

    def ssh_key(self, name="id_ed25519"):
        path = Path(self.tmp) / name
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "test@hee", "-f", str(path)], check=True, capture_output=True)
        return path

    @unittest.skipUnless(shutil.which("ssh-keygen"), "needs ssh-keygen")
    def test_seal_key_from_stdin_then_install_keys_is_idempotent_and_never_overwrites(self):
        key = self.ssh_key()
        with open(key) as f:
            r = self.tool("-seal", "spencer-id_ed25519", "-backend", "age", "-passphrase", "-dir", str(self.secrets), stdin=f)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        sealed = self.secrets / "spencer-id_ed25519.age"
        self.assertEqual(oct(sealed.stat().st_mode & 0o777), "0o600")
        self.assertIn("BEGIN AGE ENCRYPTED FILE", sealed.read_text())
        self.assertNotIn("OPENSSH PRIVATE KEY", r.stdout + r.stderr)             # key material never printed
        self.assertFalse(sealed.with_name(sealed.name + ".tmp").exists())

        r = self.tool("-install-keys", "-dir", str(self.secrets), "-account", "spencer")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        dest = self.home / ".ssh" / "id_ed25519"                                  # account prefix stripped
        self.assertEqual(dest.read_bytes(), key.read_bytes())
        self.assertEqual(oct(dest.stat().st_mode & 0o777), "0o600")
        self.assertEqual(oct((self.home / ".ssh").stat().st_mode & 0o777), "0o700")
        pub = dest.with_name("id_ed25519.pub").read_text().split()
        self.assertEqual(pub[:2], key.with_name("id_ed25519.pub").read_text().split()[:2])
        self.assertEqual(oct((self.home / ".hee" / "secrets").stat().st_mode & 0o777), "0o700")
        self.assertTrue((self.home / ".hee" / "index" / "_.yaml").exists())       # hee-trust anchor ran
        self.assertNotIn("OPENSSH PRIVATE KEY", r.stdout + r.stderr)

        r = self.tool("-install-keys", "-dir", str(self.secrets), "-account", "spencer")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("identical", r.stdout)

        dest.write_text("-----BEGIN OPENSSH PRIVATE KEY-----\ndifferent\n-----END OPENSSH PRIVATE KEY-----\n")
        r = self.tool("-install-keys", "-dir", str(self.secrets), "-account", "spencer")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("not overwritten", r.stderr)
        self.assertIn("different", dest.read_text())
        r = self.tool("-install-keys", "-dir", str(self.secrets), "-account", "spencer", "-force")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(dest.read_bytes(), key.read_bytes())

    @unittest.skipUnless(shutil.which("gpg"), "needs gpg")
    def test_pgp_secret_key_block_is_imported(self):
        src = Path(self.tmp) / "gnupg-src"; src.mkdir(mode=0o700)
        dst = Path(self.tmp) / "gnupg-dst"; dst.mkdir(mode=0o700)
        subprocess.run(["gpg", "--batch", "--quick-gen-key", "--passphrase", "", "k@test", "ed25519", "cert,sign", "0"],
                       env=dict(self.env, GNUPGHOME=str(src)), check=True, capture_output=True)
        fpr = subprocess.run(["gpg", "--list-keys", "--with-colons", "k@test"], env=dict(self.env, GNUPGHOME=str(src)),
                             capture_output=True, text=True, check=True).stdout.split("fpr:::::::::")[1].split(":")[0]
        block = subprocess.run(["gpg", "--batch", "--armor", "--export-secret-keys", fpr], env=dict(self.env, GNUPGHOME=str(src)),
                               capture_output=True, check=True).stdout
        r = subprocess.run([sys.executable, str(TOOL), "-seal", "gpg-k", "-backend", "age", "-passphrase", "-dir", str(self.secrets)],
                           env=self.env, input=block, capture_output=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = self.tool("-install-keys", "-dir", str(self.secrets), env=dict(self.env, GNUPGHOME=str(dst)))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("imported", r.stdout)
        have = subprocess.run(["gpg", "--list-secret-keys", "--with-colons"], env=dict(self.env, GNUPGHOME=str(dst)),
                              capture_output=True, text=True).stdout
        self.assertIn(fpr, have)
        self.assertNotIn("PGP PRIVATE KEY", r.stdout + r.stderr)

    def test_non_key_stdin_is_refused_unless_any_and_opens_without_identity(self):
        r = subprocess.run([sys.executable, str(TOOL), "-seal", "x", "-backend", "age", "-passphrase", "-dir", str(self.secrets)],
                           env=self.env, input="hunter2\n", capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("-any", r.stderr)
        self.assertFalse((self.secrets / "x.age").exists())
        r = subprocess.run([sys.executable, str(TOOL), "-seal", "x", "-backend", "age", "-passphrase", "-any", "-dir", str(self.secrets)],
                           env=self.env, input="hunter2\n", capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("hunter2", r.stdout + r.stderr)
        # a passphrase-sealed file needs no identity: -run opens it with age's own prompt
        env = {k: v for k, v in self.env.items() if k != "HEE_CRED_AGE_IDENTITY"}
        r = self.tool("-run", "x", "-dir", str(self.secrets), "-exec", "sh", "-c", 'test "$X" = "hunter2\n"', env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        # and -install-keys refuses to install it as a key
        r = self.tool("-install-keys", "-dir", str(self.secrets))
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("nothing written", r.stderr)
        self.assertFalse((self.home / ".ssh").exists())

    def test_passphrase_with_recipients_is_refused(self):
        r = self.tool("-seal", "x", "-backend", "age", "-passphrase", "-recipients", "age1placeholder", "-dir", str(self.secrets))
        self.assertEqual(r.returncode, 2)
        self.assertIn("-recipients", r.stderr)
        self.assertFalse(self.secrets.exists())

    @unittest.skipUnless(shutil.which("setsid") and shutil.which("ssh-keygen"), "needs setsid and ssh-keygen")
    def test_passphrase_refuses_without_a_terminal(self):
        # The real check: setsid drops the controlling terminal, so /dev/tty
        # cannot be opened and age could never ask for a passphrase.
        key = self.ssh_key()
        env = {k: v for k, v in self.env.items() if k != "HEE_CRED_TTY"}
        with open(key) as f:
            r = subprocess.run(["setsid", "-w", sys.executable, str(TOOL), "-seal", "k", "-backend", "age", "-passphrase", "-dir", str(self.secrets)],
                               env=env, stdin=f, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("terminal", r.stderr)
        self.assertFalse(self.secrets.exists())


if __name__ == "__main__":
    unittest.main()
