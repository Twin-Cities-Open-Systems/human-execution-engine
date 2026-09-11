"""hee-cred -genkey es256: seals a private key, prints a JWKS, and the sealed key signs."""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tooling" / "bin" / "hee-cred"


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
            r2 = subprocess.run([sys.executable, str(TOOL), "-pass", "issuer", "-dir", str(secrets), "-exec", "sh", "-c", 'printf "%s" "$HEE_CRED_PASS" | openssl ec -check -noout 2>&1'], env=env, capture_output=True, text=True)
            self.assertIn("EC Key valid", r2.stdout + r2.stderr)


if __name__ == "__main__":
    unittest.main()
