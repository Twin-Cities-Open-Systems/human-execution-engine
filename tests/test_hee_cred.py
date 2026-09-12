"""hee-cred: -genkey es256 seals a private key and prints a JWKS; -backend age seals and opens with an age identity."""
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


if __name__ == "__main__":
    unittest.main()
