#!/usr/bin/env python3
"""Real, minimal gopher-to-HTML proxy. Stdlib only.

Real port, 2026-08-28, for man.lab.tcos.us: this is Spencer's own
existing real app from foo.tcos.us (/usr/local/bin/gopher2html.py),
adopted here rather than reimplemented -- confirmed live, better
designed than a first hand-rolled attempt (RFC 4266 URL convention,
real image content-type handling, real open-relay guard). Only real
change: GOPHER_HOST points at the real remote upstream (foo.tcos.us)
instead of a colocated local gophernicus instance, since this
container doesn't run its own gopher daemon -- man.lab.tcos.us's own
raw Gopher access (port 70) is a separate real TCP relay
(gopher-tcp-relay, socat) to the same upstream, not this script.

Fetches over the real gopher protocol and renders menus/text as real
HTML, using the RFC 4266 URL convention (/gopher/<type-char>/<selector>).
Scoped to our own gopher backend only -- menu items pointing at a
different host/port render as a plain outbound gopher:// link instead
of being proxied, so this can't be abused as an open relay to
arbitrary gopher hosts.
"""
import html
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, quote

GOPHER_HOST = "foo.tcos.us"
GOPHER_PORT = 70
SELF_HOST = "man.lab.tcos.us"
SELF_PORT = 70

TYPE_NAMES = {
    "0": "text", "1": "menu", "9": "binary",
    "I": "image", "g": "image", "h": "html",
}

PAGE_HEAD = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%(title)s</title>
<style>
  :root { --bg:#111; --pane-bg:#1a1a1a; --text:#eee; --accent:#00ff00; --border:#333; --muted:#888; }
  * { box-sizing: border-box; }
  body { font-family: ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace;
    background: var(--bg); color: var(--text); max-width: 800px; margin: 0 auto;
    padding: 2rem 1.25rem; line-height: 1.6; }
  header { border-bottom: 1px solid var(--border); padding-bottom: 1rem; margin-bottom: 1.25rem; }
  header a { color: var(--muted); text-decoration: none; font-size: 0.85rem; }
  header a:hover { color: var(--accent); }
  .pane { background: var(--pane-bg); border: 1px solid var(--border); border-left: 3px solid var(--accent);
    border-radius: 4px; padding: 1.1rem 1.4rem; }
  .row { padding: 0.15rem 0; }
  .row a { color: var(--accent); text-decoration: none; }
  .row a:hover { text-decoration: underline; }
  .info { color: var(--muted); }
  .tag { display: inline-block; color: var(--muted); font-size: 0.72rem; width: 3.2em; }
  pre { white-space: pre-wrap; word-break: break-word; color: #ccc; }
  img { max-width: 100%%; border: 1px solid var(--border); border-radius: 4px; }
</style></head><body>
<header><a href="/gopher/1/">&larr; man.lab.tcos.us gopher root</a> &middot; <a href="/">man.lab.tcos.us</a></header>
<div class="pane">
"""
PAGE_TAIL = "</div></body></html>"


def gopher_fetch(selector: str) -> bytes:
    with socket.create_connection((GOPHER_HOST, GOPHER_PORT), timeout=10) as s:
        s.sendall((selector + "\r\n").encode())
        chunks = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks)


def render_menu(raw: bytes, cur_selector: str) -> str:
    lines = raw.decode("utf-8", errors="replace").split("\r\n")
    out = []
    for line in lines:
        if not line or line == ".":
            continue
        gtype, rest = line[0], line[1:]
        fields = rest.split("\t")
        display = fields[0] if len(fields) > 0 else ""
        sel = fields[1] if len(fields) > 1 else ""
        host = fields[2] if len(fields) > 2 else ""
        port = fields[3] if len(fields) > 3 else ""

        if gtype == "i":
            out.append(f'<div class="row info">{html.escape(display)}</div>')
            continue

        is_local = (not host) or host in (SELF_HOST, GOPHER_HOST, "localhost")
        tag = TYPE_NAMES.get(gtype, gtype)
        if is_local and gtype in ("0", "1", "9", "I", "g"):
            href = f"/gopher/{quote(gtype)}/{quote(sel)}"
            out.append(
                f'<div class="row"><span class="tag">[{tag}]</span>'
                f'<a href="{href}">{html.escape(display)}</a></div>'
            )
        else:
            # not our own backend -- link straight out via gopher://, don't proxy it
            gurl = f"gopher://{host}:{port}/{quote(gtype)}{quote(sel)}"
            out.append(
                f'<div class="row"><span class="tag">[{tag}]</span>'
                f'<a href="{gurl}">{html.escape(display)}</a> <span class="info">(external)</span></div>'
            )
    return "\n".join(out)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # journald picks up systemd unit stdout/stderr already; keep it quiet

    def do_HEAD(self):
        self._head_only = True
        self.do_GET()

    def do_GET(self):
        head_only = getattr(self, "_head_only", False)
        path = unquote(self.path)
        if path in ("/", "/gopher", "/gopher/"):
            path = "/gopher/1/"

        if not path.startswith("/gopher/"):
            self.send_response(404)
            self.end_headers()
            return

        rest = path[len("/gopher/"):]
        if len(rest) < 1:
            gtype, selector = "1", ""
        else:
            gtype, selector = rest[0], rest[2:] if len(rest) > 1 and rest[1] == "/" else rest[1:]

        try:
            raw = gopher_fetch(selector)
        except OSError as e:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            if not head_only:
                self.wfile.write(f"gopher backend error: {e}".encode())
            return

        if gtype == "1":
            title = selector or "gopher root"
            body = render_menu(raw, selector)
            page = (PAGE_HEAD % {"title": html.escape(f"gopher: {title}")}) + body + PAGE_TAIL
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if not head_only:
                self.wfile.write(page.encode())
        elif gtype == "0":
            text = raw.decode("utf-8", errors="replace")
            page = (PAGE_HEAD % {"title": html.escape(selector)}) + f"<pre>{html.escape(text)}</pre>" + PAGE_TAIL
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if not head_only:
                self.wfile.write(page.encode())
        elif gtype in ("I", "g", "9"):
            ctype = "application/octet-stream"
            low = selector.lower()
            if low.endswith(".png"):
                ctype = "image/png"
            elif low.endswith((".jpg", ".jpeg")):
                ctype = "image/jpeg"
            elif low.endswith(".gif"):
                ctype = "image/gif"
            elif low.endswith(".asc") or low.endswith(".txt") or "sha256sums" in low:
                ctype = "text/plain; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.end_headers()
            if not head_only:
                self.wfile.write(raw)
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            if not head_only:
                self.wfile.write(f"unsupported gopher type: {gtype!r}".encode())


if __name__ == "__main__":
    # Real difference from foo's own copy: 0.0.0.0, not 127.0.0.1 --
    # foo's real app sits behind its own local nginx/whatever handles
    # the public bind; this container has nothing in front of it,
    # haproxy on pve needs to reach this port directly.
    srv = ThreadingHTTPServer(("0.0.0.0", 8070), Handler)
    print("gopher2html: listening on :8070, upstream gopher://foo.tcos.us:70")
    srv.serve_forever()
