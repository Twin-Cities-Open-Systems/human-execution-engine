"""hee_ghapp, and hee-cred -github-app / -github-token, against a fake GitHub API on localhost.

The fake checks what GitHub checks: the JWT's RS256 signature against the App's public key, its issuer and its
lifetime; a token for the repository listing; and it records every token it mints and every revoke."""
import base64, json, os, shutil, subprocess, sys, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "library" / "py"))
import hee_ghapp as gh  # noqa: E402

TOOL = ROOT / "tooling" / "bin" / "hee-cred"
try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False

REPOS = ["alpha", "beta", "gamma"]
CEILING = {"contents": "write", "issues": "write", "metadata": "read", "pull_requests": "write"}
CLIENT_ID = "Iv1.fixture"


def rsa_pem():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                            serialization.NoEncryption()).decode()
    return key, pem


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class FakeGitHub:
    """One org installation (id 42) that can see REPOS. `tamper` is merged into the permissions of every
    non-probe token, the way a misconfigured or changed installation would answer."""

    def __init__(self, public_key):
        self.public_key, self.tokens, self.revoked, self.tamper = public_key, {}, [], None
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, code, doc=None):
                body = json.dumps(doc).encode() if doc is not None else b""
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def bearer(self):
                return self.headers.get("Authorization", "").removeprefix("Bearer ")

            def jwt_ok(self):
                try:
                    h, c, s = self.bearer().split(".")
                    fake.public_key.verify(b64d(s), f"{h}.{c}".encode(), padding.PKCS1v15(), hashes.SHA256())
                    claims = json.loads(b64d(c))
                    return claims["iss"] == CLIENT_ID and claims["exp"] - claims["iat"] <= 600
                except Exception:  # noqa: BLE001 -- any malformed or foreign JWT is a 401, as on GitHub
                    return False

            def live_token(self):
                t = self.bearer()
                return fake.tokens.get(t) if t not in fake.revoked else None

            def do_GET(self):
                if self.path == "/orgs/test-org/installation":
                    if not self.jwt_ok():
                        return self.send(401, {"message": "A JSON web token could not be decoded"})
                    return self.send(200, {"id": 42, "app_slug": "fixture", "repository_selection": "all",
                                           "permissions": CEILING})
                if self.path.startswith("/installation/repositories"):
                    t = self.live_token()
                    if not t:
                        return self.send(401, {"message": "Bad credentials"})
                    return self.send(200, {"total_count": len(t["repositories"]),
                                           "repositories": [{"name": n} for n in t["repositories"]]})
                self.send(404, {"message": "Not Found"})

            def do_POST(self):
                if self.path != "/app/installations/42/access_tokens" or not self.jwt_ok():
                    return self.send(401, {"message": "A JSON web token could not be decoded"})
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                perms = dict(body.get("permissions") or {})
                if fake.tamper and perms != {"metadata": "read"}:
                    perms.update(fake.tamper)
                token = f"ghs_fixture{len(fake.tokens)}"
                repos = body.get("repositories") or REPOS
                fake.tokens[token] = {"repositories": repos, "permissions": perms}
                self.send(201, {"token": token, "expires_at": "2026-09-13T20:00:00Z", "permissions": perms,
                                "repository_selection": "selected" if body.get("repositories") else "all",
                                "repositories": [{"name": n} for n in repos]})

            def do_DELETE(self):
                if self.path == "/installation/token" and self.live_token():
                    fake.revoked.append(self.bearer())
                    return self.send(204)
                self.send(401, {"message": "Bad credentials"})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.api = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class Registry(unittest.TestCase):
    def test_grant_above_the_ceiling_is_refused_naming_every_excess(self):
        with self.assertRaises(gh.GitHubAppError) as cm:
            gh.check_permissions({"contents": "admin", "workflows": "write", "issues": "read"}, CEILING)
        msg = str(cm.exception)
        self.assertIn("contents=admin (the App's ceiling is write)", msg)
        self.assertIn("workflows=write (not in the App's ceiling)", msg)
        self.assertNotIn("issues", msg)

    def test_agent_roster_supplies_the_repos_and_metadata_is_implied(self):
        with tempfile.TemporaryDirectory() as d:
            reg = Path(d) / "github-apps.registry.v1.yaml"
            (Path(d) / "agent-roster.registry.v1.yaml").write_text(
                'spec:\n  agents:\n    docs-keeper:\n      scope:\n        repos: "^(alpha|beta)$"\n')
            app = {"permissions": CEILING,
                   "grants": {"docs-keeper": {"repos": "agent-roster", "permissions": {"contents": "write"}}}}
            self.assertEqual(gh.resolve_grant(app, "docs-keeper", str(reg)),
                             ({"contents": "write", "metadata": "read"}, "^(alpha|beta)$"))
            with self.assertRaisesRegex(gh.GitHubAppError, "no grant 'ci-triage'"):
                gh.resolve_grant(app, "ci-triage", str(reg))

    def test_registration_url_asks_for_the_ceiling_private_with_no_webhook(self):
        url = gh.registration_url("Twin-Cities-Open-Systems",
                                  {"registration": {"name": "TCOS Agents", "url": "https://tcos.us"}, "permissions": CEILING})
        u, q = urlsplit(url), parse_qs(urlsplit(url).query)
        self.assertEqual((u.netloc, u.path), ("github.com", "/organizations/Twin-Cities-Open-Systems/settings/apps/new"))
        self.assertEqual((q["name"], q["public"], q["webhook_active"], q["contents"], q["pull_requests"]),
                         (["TCOS Agents"], ["false"], ["false"], ["write"], ["write"]))
        self.assertNotIn("metadata", q)

    def test_installation_drift_more_is_critical_less_is_warning(self):
        out = gh.compare_installation({"permissions": {"contents": "write", "administration": "read", "metadata": "read"}},
                                      {"contents": "write", "issues": "write", "metadata": "read"})
        self.assertEqual(len(out), 2)
        self.assertIn(("CRITICAL", "installation holds administration=read; the registry's ceiling is nothing"), out)
        self.assertTrue(any(level == "WARNING" and "issues" in m for level, m in out))

    def test_store_is_the_secrets_dir_beside_the_registry(self):
        self.assertEqual(gh.store_dir("/r/fleet-ops/hee/registries/github-apps.registry.v1.yaml"),
                         Path("/r/fleet-ops/.hee/secrets"))


@unittest.skipUnless(HAVE_CRYPTO, "needs python3-cryptography")
class Mint(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key, cls.pem = rsa_pem()

    def setUp(self):
        self.fake = FakeGitHub(self.key.public_key())

    def tearDown(self):
        self.fake.close()

    def test_jwt_is_rs256_backdated_sixty_seconds_and_ten_minutes_long(self):
        h, c, s = gh.app_jwt(self.pem, CLIENT_ID, now=1_000_000).split(".")
        self.assertEqual(json.loads(b64d(h))["alg"], "RS256")
        self.assertEqual(json.loads(b64d(c)), {"iat": 999_940, "exp": 1_000_540, "iss": CLIENT_ID})
        self.key.public_key().verify(b64d(s), f"{h}.{c}".encode(), padding.PKCS1v15(), hashes.SHA256())

    def test_a_pattern_is_narrowed_to_visible_repos_and_the_probe_is_revoked(self):
        tok = gh.mint(self.pem, CLIENT_ID, "test-org", {"contents": "write", "metadata": "read"}, "^(alpha|gamma)$",
                      api=self.fake.api)
        self.assertEqual((tok["repositories"], tok["permissions"], tok["installation_id"]),
                         (["alpha", "gamma"], {"contents": "write", "metadata": "read"}, 42))
        probes = [t for t, v in self.fake.tokens.items() if v["permissions"] == {"metadata": "read"}]
        self.assertEqual(len(probes), 1)
        self.assertEqual(self.fake.revoked, probes)             # the probe, and only the probe, is gone
        self.assertTrue(gh.revoke(tok["token"], api=self.fake.api))
        self.assertFalse(gh.revoke(tok["token"], api=self.fake.api))   # a dead token cannot be revoked twice

    def test_a_pattern_matching_nothing_is_refused(self):
        with self.assertRaisesRegex(gh.GitHubAppError, "matches none of the 3 repositories"):
            gh.mint(self.pem, CLIENT_ID, "test-org", {"metadata": "read"}, "^nope$", api=self.fake.api)

    def test_a_token_carrying_unasked_permissions_is_revoked_and_refused(self):
        self.fake.tamper = {"administration": "write"}
        with self.assertRaisesRegex(gh.GitHubAppError, "token revoked, not used"):
            gh.mint(self.pem, CLIENT_ID, "test-org", {"contents": "read", "metadata": "read"}, ["beta"], api=self.fake.api)
        tampered = [t for t, v in self.fake.tokens.items() if "administration" in v["permissions"]]
        self.assertEqual(len(tampered), 1)
        self.assertIn(tampered[0], self.fake.revoked)

    def test_a_jwt_from_another_key_is_rejected_by_github(self):
        _, other = rsa_pem()
        with self.assertRaisesRegex(gh.GitHubAppError, "HTTP 401"):
            gh.mint(other, CLIENT_ID, "test-org", {"metadata": "read"}, ["alpha"], api=self.fake.api)
        self.assertEqual(self.fake.tokens, {})


REGISTRY = """spec:
  org: test-org
  apps:
    fixture:
      cred: github-app-fixture
      client_id: {client_id}
      seal_recipients: [{fpr}]
      registration: {{name: Fixture, url: https://example.test}}
      permissions: {{contents: write, issues: write, metadata: read, pull_requests: write}}
      grants:
        bot: {{repos: "^(alpha|beta)$", permissions: {{contents: write, pull_requests: write}}}}
"""


@unittest.skipUnless(HAVE_CRYPTO and shutil.which("gpg") and shutil.which("openssl"),
                     "needs python3-cryptography, gpg and openssl")
class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.env = dict(os.environ, GNUPGHOME=str(d))
        self.env.pop("HEE_CRED_DIR", None)
        self.env.pop("HEE_GITHUB_APPS", None)
        subprocess.run(["gpg", "--batch", "--quick-gen-key", "--passphrase", "", "t@test", "ed25519", "cert,sign", "0"],
                       env=self.env, check=True, capture_output=True)
        self.fpr = subprocess.run(["gpg", "--list-keys", "--with-colons", "t@test"], env=self.env, capture_output=True,
                                  text=True).stdout.split("fpr:::::::::")[1].split(":")[0]
        subprocess.run(["gpg", "--batch", "--quick-add-key", "--passphrase", "", self.fpr, "cv25519", "encr", "0"],
                       env=self.env, check=True, capture_output=True)
        self.key, pem = rsa_pem()
        self.fake = FakeGitHub(self.key.public_key())
        self.env["HEE_GITHUB_API"] = self.fake.api
        self.reg = d / "repo" / "hee" / "registries" / "github-apps.registry.v1.yaml"
        self.reg.parent.mkdir(parents=True)
        self.store = d / "repo" / ".hee" / "secrets"
        self.pem_file = d / "download.pem"
        self.pem_file.write_text(pem)

    def tearDown(self):
        self.fake.close()
        self.tmp.cleanup()

    def write_registry(self, client_id=CLIENT_ID):
        self.reg.write_text(REGISTRY.format(client_id=client_id, fpr=self.fpr))

    def tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), *args], env=self.env, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, cwd=self.tmp.name)

    def test_unregistered_prints_the_prefilled_registration_link(self):
        self.write_registry("null")
        r = self.tool("-github-app", "github-app-fixture", "-registry", str(self.reg))
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("https://github.com/organizations/test-org/settings/apps/new?name=Fixture", r.stdout)

    def test_seal_check_and_a_token_that_lives_as_long_as_the_command(self):
        self.write_registry()
        r = self.tool("-github-app", "github-app-fixture", "-registry", str(self.reg), "-key", str(self.pem_file))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.store / "github-app-fixture.gpg").is_file())       # beside the registry, not in cwd
        self.assertNotIn("PRIVATE KEY", r.stdout + r.stderr)

        r = self.tool("-github-app", "github-app-fixture", "-registry", str(self.reg), "-key", str(self.pem_file))
        self.assertEqual(r.returncode, 2)
        self.assertIn("-force", r.stderr)                                        # no silent overwrite of a sealed key

        r = self.tool("-github-app", "github-app-fixture", "-registry", str(self.reg))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("installation permissions match the registry's ceiling", r.stdout)

        child = 'test -z "${HEE_CRED_PASS:-}" && test -z "${GITHUB_APP_FIXTURE:-}" && printf %s "$GH_TOKEN"'
        r = self.tool("-run", "github-app-fixture", "-github-token", "bot", "-registry", str(self.reg),
                      "-exec", "sh", "-c", child)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        token = r.stdout
        self.assertTrue(token.startswith("ghs_fixture"), token)
        self.assertEqual(self.fake.tokens[token], {"repositories": ["alpha", "beta"],
                                                   "permissions": {"contents": "write", "metadata": "read",
                                                                   "pull_requests": "write"}})
        self.assertIn(token, self.fake.revoked)                                  # revoked when the command exited
        self.assertNotIn(token, r.stderr)
        self.assertNotIn("PRIVATE KEY", r.stderr)

    def test_the_child_exit_code_is_the_tools_exit_code_and_the_token_still_dies(self):
        self.write_registry()
        self.assertEqual(self.tool("-github-app", "github-app-fixture", "-registry", str(self.reg), "-key",
                                   str(self.pem_file)).returncode, 0)
        r = self.tool("-pass", "github-app-fixture", "-github-token", "bot", "-registry", str(self.reg),
                      "-exec", "sh", "-c", "exit 7")
        self.assertEqual(r.returncode, 7, r.stdout + r.stderr)
        self.assertEqual(len(self.fake.revoked), 2)                              # the probe and the job's token

    def test_a_grant_above_the_ceiling_never_reaches_github(self):
        self.write_registry()
        self.assertEqual(self.tool("-github-app", "github-app-fixture", "-registry", str(self.reg), "-key",
                                   str(self.pem_file)).returncode, 0)
        self.reg.write_text(self.reg.read_text().replace("contents: write, pull_requests: write}",
                                                         "contents: write, administration: write}"))
        r = self.tool("-run", "github-app-fixture", "-github-token", "bot", "-registry", str(self.reg),
                      "-exec", "true")
        self.assertEqual(r.returncode, 2)
        self.assertIn("administration=write (not in the App's ceiling)", r.stderr)
        self.assertEqual(self.fake.tokens, {})

    def test_a_key_that_is_not_rsa_is_not_sealed(self):
        self.write_registry()
        self.pem_file.write_bytes(subprocess.run(["openssl", "genpkey", "-algorithm", "EC", "-pkeyopt",
                                                  "ec_paramgen_curve:P-256"], capture_output=True, check=True).stdout)
        r = self.tool("-github-app", "github-app-fixture", "-registry", str(self.reg), "-key", str(self.pem_file))
        self.assertEqual(r.returncode, 2)
        self.assertIn("not an RSA key", r.stderr)
        self.assertFalse((self.store / "github-app-fixture.gpg").exists())


if __name__ == "__main__":
    unittest.main()
