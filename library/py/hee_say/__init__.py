"""hee_say -- text to a tagged audio album: the testable half of tooling/bin/hee-say.

Three jobs, none of which needs a speech engine, so all of it runs in CI:

  1. NORMALIZE. Prose becomes text a speech engine pronounces correctly. An
     agent cannot listen to its own output, so every rule here was settled by
     reading the engine's phonemes, not by ear (measured 2026-10-04):
       - ``A P R S`` is read "uh P R S" and bare ``APRS`` becomes a word;
         ``A-P-R-S`` is read as four letters. Acronyms are therefore spelled
         with hyphens, plurals as ``L-E-D's``.
       - shouted words (``THE RADIO``) are lowercased, or they get spelled.
       - a decimal's point is read as a full stop, so ``144.39`` is written
         "144 point 3 9".
  2. READ. Markdown, plain text, PDF text and YAML/JSON records become an
     ordered list of ``(spoken text, pause after, shown text)`` blocks. The
     shown text is the source's own wording: it becomes the track's lyrics,
     timed line by line, so a player shows "APRS" while the voice says it.
  3. DESCRIBE. An album is a hee/v1 Card (labels.artifact: say-album) and a
     pronunciation lexicon is a hee/v1 Registry (labels.artifact:
     say-lexicon). ``album_from_sources`` builds the same Album from loose
     files, so an ad hoc run and a committed object take one code path.

Synthesis itself is ``worker.py`` beside this file, run under the engine's own
venv; encoding is one ffmpeg call whose argv ``ffmpeg_cmd`` builds here.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

VERSION = 1
ALBUM_ARTIFACT = "say-album"
LEXICON_ARTIFACT = "say-lexicon"

# What an album gets when nothing says otherwise. These are the settings the
# first real album (11 tracks, 2026-10-04) was built with.
DEFAULTS = {
    "engine": "kokoro",
    "voice": "af_heart",
    "lang": "en-us",
    "speed": 1.0,
    "genre": "Speech",
    "bitrate": "64k",
    "artist": "Unknown Artist",
}
PAUSE = {"lead": 0.4, "intro": 0.9, "paragraph": 0.55, "before_heading": 0.9,
         "heading": 0.7, "item": 0.35, "record": 0.5}
TEXT_SUFFIXES = (".md", ".markdown", ".txt", ".pdf")

# Typography that has no sound of its own. Ordered; a lexicon's spec.symbols
# replaces an entry or adds one.
SYMBOLS = [("→", ", to "), ("—", ", "), ("–", " to "), ("+", " plus "),
           ("&", " and "), ("%", " percent "), ("=", " equals "),
           ("×", " times "), ("÷", " divided by "), ("/", " or "), ("|", ". ")]
DIGIT_WORDS = "zero one two three four five six seven eight nine".split()


class SayError(Exception):
    """An input that must not become audio: CRITICAL."""


# --- lexicon -----------------------------------------------------------------

@dataclass
class Lexicon:
    acronyms: list = field(default_factory=list)
    rules: list = field(default_factory=list)      # (compiled regex, replacement or callable)
    symbols: list = field(default_factory=lambda: list(SYMBOLS))

    def merge_object(self, obj: dict, origin: str = "lexicon") -> None:
        spec = envelope(obj, "Registry", LEXICON_ARTIFACT, origin)
        for a in spec.get("acronyms") or []:
            if not re.fullmatch(r"[A-Z0-9]{2,}", str(a)):
                raise SayError(f"{origin}: acronym {a!r} is not upper-case letters and digits")
            if a not in self.acronyms:
                self.acronyms.append(str(a))
        for i, rule in enumerate(spec.get("rules") or []):
            self.rules.append(compile_rule(rule, f"{origin}: rules[{i}]"))
        for sym, say in (spec.get("symbols") or {}).items():
            self.symbols = [(s, w) for s, w in self.symbols if s != sym] + [(sym, say)]


def _spell_letters(m) -> str:
    """W1AW -> "W one A-W". Letter runs are hyphenated, digits are separate
    words: inside one hyphen chain ("W-one-A-W") the engine reads the A after
    a digit word as the article "uh" (measured 2026-10-05)."""
    runs = re.findall(r"\d|[^\d]+", m.group(0))
    return " ".join(DIGIT_WORDS[int(r)] if r.isdigit() else "-".join(r) for r in runs)


def compile_rule(rule: dict, origin: str):
    if not isinstance(rule, dict) or "match" not in rule or ("say" in rule) == ("spell" in rule):
        raise SayError(f"{origin}: a rule is {{match, say}} or {{match, spell: digits|letters}}")
    try:
        pat = re.compile(rule["match"])
    except re.error as e:
        raise SayError(f"{origin}: bad regex {rule['match']!r}: {e}") from None
    if "say" in rule:
        return pat, str(rule["say"])
    if rule["spell"] == "digits":
        return pat, lambda m: " ".join(m.group(0))
    if rule["spell"] == "letters":
        return pat, _spell_letters
    raise SayError(f"{origin}: spell is digits or letters, not {rule['spell']!r}")


def load_lexicon(paths) -> Lexicon:
    lex = Lexicon()
    for p in paths:
        lex.merge_object(read_yaml(p), str(p))
    return lex


# --- normalize ---------------------------------------------------------------

def _spell_acronym(m):
    return "-".join(m.group(1)) + ("'s" if m.group(2) else "")


def speak(text: str, lex: Lexicon) -> str:
    """Prose (markdown inline marks allowed) -> text the engine says correctly."""
    s = text.replace("’", "'").replace("‘", "'")
    for q in "“”\"`":
        s = s.replace(q, "")
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)                 # images say nothing
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)             # a link is its text
    s = re.sub(r"https?://([^\s/)>]+)\S*", lambda m: m.group(1).replace(".", " dot "), s)
    for pat, rep in lex.rules:
        s = pat.sub(rep, s)
    # 144.39 is read "one hundred forty four. thirty nine" -- the point becomes
    # a full stop -- so a decimal's point and its digits are written out.
    s = re.sub(r"(?<![\d.])(\d+)\.(\d+)(?![\d.]|\.\d)", lambda m: f"{m.group(1)} point {' '.join(m.group(2))}", s)
    s = s.replace("*", "")
    s = re.sub(r"\?\s*→", "?", s)
    for sym, say in lex.symbols:
        s = re.sub(r"\s*" + re.escape(sym) + r"\s*", say, s)
    if lex.acronyms:
        s = re.sub(r"\b(%s)(s?)\b" % "|".join(sorted(lex.acronyms, key=len, reverse=True)), _spell_acronym, s)
    return re.sub(r"\s+", " ", s).replace(" ,", ",").strip()


def finish(text: str, leftover: set | None = None) -> str:
    """Lowercase shouted words (after noting them) and end the sentence."""
    if leftover is not None:
        leftover.update(re.findall(r"(?<![\w-])[A-Z][A-Z0-9]+(?![\w-])", text))
    s = re.sub(r"(?<![\w-])[A-Z]{2,}(?![\w-])", lambda m: m.group(0).lower(), text)
    s = re.sub(r"([.?!])\.+", r"\1", s.rstrip(",; "))    # "answer.." from a template
    if s and s[-1] not in ".?!:":
        s += "."
    return s


def show(text: str) -> str:
    """The same prose as a reader should see it: markdown marks gone, words kept."""
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\*\*|`", "", s)
    s = re.sub(r"(?<![\w*])\*(?=\S)|(?<=\S)\*(?![\w*])", "", s)
    return re.sub(r"\s+", " ", s).strip()


def block(text: str, pause: float, lex: Lexicon, leftover=None, shown: str | None = None):
    """One (spoken, pause, shown) block, or None when nothing would be said."""
    said = finish(speak(text, lex), leftover)
    return (said, pause, show(shown if shown is not None else text)) if said else None


def unpronounceable(leftover) -> list:
    """Leftover upper-case tokens an engine will likely mangle once lowercased:
    no vowel, or a digit. Ordinary shouted words (THE, RADIO) are not these."""
    return sorted(t for t in leftover if re.search(r"\d", t) or not re.search(r"[AEIOUY]", t))


# --- sources -> blocks -------------------------------------------------------

def _rewrite(line: str, opts: dict) -> str | None:
    for pat in opts.get("drop") or []:
        if re.search(pat, line):
            return None
    for rule in opts.get("rewrite") or []:
        line = re.sub(rule["match"], rule["say"], line)
    return line


def blocks_markdown(text: str, lex: Lexicon, opts: dict | None = None, leftover=None):
    """Markdown -> blocks. The H1 is dropped unless skip_h1 is false
    (the track's intro already says the title); fenced code says nothing."""
    opts = opts or {}
    out, para, fenced, numbered = [], [], False, [None]

    def flush(pause=PAUSE["paragraph"]):
        if para:
            text = " ".join(para)
            # "3: text" is said as a count; a reader sees the list's own "3. text"
            b = block(f"{numbered[0]}: {text}" if numbered[0] else text, pause, lex, leftover,
                      shown=f"{numbered[0]}. {text}" if numbered[0] else text)
            para.clear()
            numbered[0] = None
            if b:
                out.append(b)

    for raw in text.splitlines():
        line = raw.rstrip()
        if re.match(r"\s*(```|~~~)", line):
            fenced = not fenced
            flush()
            continue
        if fenced:
            continue
        line = re.sub(r"<!--.*?-->", "", re.sub(r"^\s*>\s?", "", line)).strip()
        if not line or re.fullmatch(r"[-*_=]{3,}|\|?[\s:|-]+\|[\s:|-]*", line):
            flush()
            continue
        if re.match(r"#\s", line) and opts.get("skip_h1", True):
            continue
        line = _rewrite(line, opts)
        if line is None:
            continue
        if line.startswith("#"):
            flush(PAUSE["before_heading"])
            out.append(block(line.lstrip("# "), PAUSE["heading"], lex, leftover))
            continue
        m = re.match(r"(?:[-*+]|(\d+)\.)\s+(.*)", line)
        if m:
            flush(PAUSE["item"])
            para.append(m.group(2))
            numbered[0] = m.group(1)
            flush(PAUSE["item"])
        else:
            para.append(line)
    flush()
    return out


def blocks_text(text: str, lex: Lexicon, opts: dict | None = None, leftover=None):
    """Plain text -> one block per blank-line-separated paragraph."""
    out = []
    for para in re.split(r"\n\s*\n", text):
        lines = [_rewrite(ln.strip(), opts or {}) for ln in para.splitlines()]
        b = block(" ".join(ln for ln in lines if ln), PAUSE["paragraph"], lex, leftover)
        if b:
            out.append(b)
    return out


def blocks_pdf_text(text: str, lex: Lexicon, opts: dict | None = None, leftover=None):
    """A PDF's extracted text -> blocks. Extraction returns wrapped lines with
    no paragraph marks, so the part names each paragraph's opening words
    (``paragraphs``); without them the whole document is one block."""
    opts = opts or {}
    flat = " ".join(text.split())
    prefix = opts.get("skip_prefix")
    if prefix:
        if not flat.startswith(prefix):
            raise SayError(f"pdf text does not start with skip_prefix {prefix!r}")
        flat = flat[len(prefix):].strip()
    for opener in opts.get("paragraphs") or []:
        if opener not in flat:
            raise SayError(f"pdf text has no paragraph opening {opener!r}")
        flat = flat.replace(opener, "\n\n" + opener, 1)
    return blocks_text(flat, lex, opts, leftover)


def dig(obj, dotted: str):
    for key in dotted.split("."):
        obj = obj.get(key) if isinstance(obj, dict) else None
    return obj


def render_record(item: dict, say) -> str:
    """say is a template, or a list of {when: FIELD, say: TEMPLATE} tried in
    order (when omitted always matches; a FIELD matches when it is not empty)."""
    for alt in ([{"say": say}] if isinstance(say, str) else say):
        if "when" in alt and dig(item, alt["when"]) in (None, "", [], {}):
            continue

        def fill(m):
            v = dig(item, m.group(1))
            if v is None:
                raise SayError(f"record has no field {m.group(1)!r}: {str(item)[:80]}")
            return "; ".join(str(x) for x in v) if isinstance(v, list) else str(v)
        return re.sub(r"\{([\w.]+)\}", fill, alt["say"])
    raise SayError(f"no `say` alternative matches record: {str(item)[:80]}")


def blocks_records(data, lex: Lexicon, opts: dict, leftover=None):
    """A YAML/JSON document -> one block per record under ``items`` that passes
    ``where`` (field: value, null allowed), spoken through ``say``. With
    ``group_by`` (a field), ``group_heading`` is said each time that field's
    value changes, rendered from the first record of the group."""
    items = dig(data, opts["items"]) if opts.get("items") else data
    if not isinstance(items, list):
        raise SayError(f"records: {opts.get('items') or 'document'} is not a list")
    if "say" not in opts:
        raise SayError("records: the part needs a `say` template")
    out, group = [], object()
    for item in items:
        if not all(dig(item, k) == v for k, v in (opts.get("where") or {}).items()):
            continue
        if opts.get("group_by") and dig(item, opts["group_by"]) != group:
            group = dig(item, opts["group_by"])
            if out:
                out[-1] = (out[-1][0], PAUSE["before_heading"], out[-1][2])
            out.append(block(render_record(item, opts.get("group_heading", "{%s}." % opts["group_by"])),
                             PAUSE["heading"], lex, leftover))
        out.append(block(render_record(item, opts["say"]), PAUSE["record"], lex, leftover))
    return out


def part_format(part: dict) -> str:
    if part.get("format"):
        return part["format"]
    suffix = Path(part["source"]).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in (".md", ".markdown"):
        return "markdown"
    if suffix in (".yaml", ".yml", ".json"):
        return "records"
    return "text"


def blocks_part(part: dict, root: Path, lex: Lexicon, leftover=None, pdf_text=None):
    path = (root / part["source"]).resolve() if not os.path.isabs(part["source"]) else Path(part["source"])
    if not path.is_file():
        raise SayError(f"no such source: {path}")
    fmt = part_format(part)
    out = []
    if part.get("heading"):
        out.append(block(part["heading"], PAUSE["heading"], lex, leftover))
    if fmt == "pdf":
        if pdf_text is None:
            raise SayError(f"{path.name}: a PDF source needs the engine venv (hee say setup)")
        out += blocks_pdf_text(pdf_text(path), lex, part, leftover)
    elif fmt == "records":
        out += blocks_records(read_yaml(path), lex, part, leftover)
    elif fmt == "markdown":
        out += blocks_markdown(path.read_text(), lex, part, leftover)
    elif fmt == "text":
        out += blocks_text(path.read_text(), lex, part, leftover)
    else:
        raise SayError(f"{path.name}: unknown format {fmt!r}")
    return out


# --- the album ---------------------------------------------------------------

@dataclass
class Track:
    title: str
    parts: list
    spoken: str | None = None
    intro: str | None = None
    comment: str | None = None


@dataclass
class Album:
    artist: str
    album: str
    year: int
    tracks: list
    root: Path                      # relative part sources resolve here
    genre: str = DEFAULTS["genre"]
    voice: str = DEFAULTS["voice"]
    lang: str = DEFAULTS["lang"]
    speed: float = DEFAULTS["speed"]
    engine: str = DEFAULTS["engine"]
    bitrate: str = DEFAULTS["bitrate"]
    intro: str = "{spoken}."
    cover: Path | None = None
    lexicons: list = field(default_factory=list)
    name: str | None = None
    description: str | None = None

    def override(self, **kw):
        for k, v in kw.items():
            if v is not None:
                setattr(self, k, v)
        return self


def read_yaml(path):
    import yaml
    try:
        with open(path) as fh:
            return json.load(fh) if str(path).endswith(".json") else yaml.safe_load(fh)
    except (OSError, ValueError, yaml.YAMLError) as e:
        raise SayError(f"cannot read {path}: {e}") from None


def envelope(obj, kind: str, artifact: str, origin: str) -> dict:
    """The spec of a hee/v1 object of this kind and artifact, or SayError."""
    if not isinstance(obj, dict) or obj.get("apiVersion") != "hee/v1":
        raise SayError(f"{origin}: not a hee/v1 object")
    meta = obj.get("metadata") or {}
    if obj.get("kind") != kind or (meta.get("labels") or {}).get("artifact") != artifact:
        raise SayError(f"{origin}: expected kind {kind} with labels.artifact {artifact}")
    if not isinstance(obj.get("spec"), dict):
        raise SayError(f"{origin}: no spec")
    return obj["spec"]


def is_album_card(path) -> bool:
    if Path(path).suffix.lower() not in (".yaml", ".yml"):
        return False
    try:
        obj = read_yaml(path)
    except SayError:
        return False
    return (isinstance(obj, dict) and obj.get("kind") == "Card"
            and ((obj.get("metadata") or {}).get("labels") or {}).get("artifact") == ALBUM_ARTIFACT)


def load_card(path, src=None) -> Album:
    """An album Card -> Album. Lexicon and cover paths are relative to the
    card; part sources are relative to ``src`` when given, else to the card."""
    path = Path(path).resolve()
    obj = read_yaml(path)
    spec = envelope(obj, "Card", ALBUM_ARTIFACT, path.name)
    for key in ("artist", "album", "year", "tracks"):
        if not spec.get(key):
            raise SayError(f"{path.name}: spec.{key} is required")
    defaults = spec.get("defaults") or {}
    tracks = []
    for i, t in enumerate(spec["tracks"], 1):
        parts = t.get("parts") or ([{"source": t["source"]}] if t.get("source") else [])
        parts = [{**defaults, **p} for p in parts]
        if not t.get("title") or not parts:
            raise SayError(f"{path.name}: track {i} needs a title and a source or parts")
        for p in parts:
            if not p.get("source"):
                raise SayError(f"{path.name}: track {i} has a part with no source")
        tracks.append(Track(title=str(t["title"]), parts=parts,
                            spoken=t.get("spoken"), intro=t.get("intro"), comment=t.get("comment")))
    voice = spec.get("voice") or {}
    lex = spec.get("lexicon") or []
    return Album(
        artist=str(spec["artist"]), album=str(spec["album"]), year=int(spec["year"]), tracks=tracks,
        root=Path(src).resolve() if src else path.parent,
        genre=spec.get("genre", DEFAULTS["genre"]), voice=voice.get("name", DEFAULTS["voice"]),
        lang=voice.get("lang", DEFAULTS["lang"]), speed=float(voice.get("speed", DEFAULTS["speed"])),
        engine=voice.get("engine", DEFAULTS["engine"]), bitrate=spec.get("bitrate", DEFAULTS["bitrate"]),
        intro=spec.get("intro", "{spoken}."), cover=(path.parent / spec["cover"]) if spec.get("cover") else None,
        lexicons=[path.parent / p for p in ([lex] if isinstance(lex, str) else lex)],
        name=(obj.get("metadata") or {}).get("name"), description=(obj.get("metadata") or {}).get("description"))


def title_of(path: Path) -> str:
    if path.suffix.lower() in (".md", ".markdown"):
        m = re.search(r"^#\s+(.+)$", path.read_text(), re.M)
        if m:
            return re.sub(r"[*_`]", "", m.group(1)).strip()
    # 02-antennas.txt -> "Antennas": a leading number is file order, not a title
    words = re.sub(r"[_-]+", " ", re.sub(r"^\d+[\s._-]+", "", path.stem)).strip() or path.stem
    return words[0].upper() + words[1:]


def album_from_sources(sources, artist=None, album=None, year=None) -> Album:
    """Loose files and directories -> Album: one track per file, in the order
    given (a directory contributes its text files, sorted by name)."""
    files = []
    for s in map(Path, sources):
        if s.is_dir():
            files += sorted(p for p in s.iterdir() if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES)
        elif s.is_file():
            files.append(s)
        else:
            raise SayError(f"no such source: {s}")
    if not files:
        raise SayError("no text sources found (.md, .markdown, .txt, .pdf)")
    first = Path(sources[0]).resolve()
    return Album(
        artist=artist or os.environ.get("HEE_SAY_ARTIST") or DEFAULTS["artist"],
        album=album or re.sub(r"[_-]+", " ", (first if first.is_dir() else first.parent).name),
        year=int(year or datetime.date.today().year), root=Path.cwd(),
        tracks=[Track(title=title_of(f), parts=[{"source": str(f.resolve())}]) for f in files])


def card_object(album: Album) -> dict:
    """The Album as a hee/v1 Card, ready to commit. inuid is null/soa_pending:
    a real tracked object whose provenance identity awaits the identity epoch."""
    slug = re.sub(r"[^a-z0-9]+", "-", f"{album.artist} {album.album}".lower()).strip("-")
    tracks = []
    for t in album.tracks:
        entry = {"title": t.title}
        for key in ("spoken", "intro", "comment"):
            if getattr(t, key):
                entry[key] = getattr(t, key)
        entry["parts"] = [dict(p, source=os.path.relpath(p["source"], album.root)) if os.path.isabs(p["source"])
                          else p for p in t.parts]
        tracks.append(entry)
    return {
        "apiVersion": "hee/v1", "kind": "Card",
        "metadata": {
            "name": album.name or f"say-{slug}",
            "description": album.description or f"Spoken album: {album.album}, by {album.artist}",
            "labels": {"hee.object": "true", "artifact": ALBUM_ARTIFACT},
            "annotations": {"inuid": None, "inuid_null_reason": "soa_pending"},
        },
        "spec": {
            "artist": album.artist, "album": album.album, "year": album.year, "genre": album.genre,
            "voice": {"engine": album.engine, "name": album.voice, "lang": album.lang, "speed": album.speed},
            "bitrate": album.bitrate, "intro": album.intro, "tracks": tracks,
        },
    }


# --- plan, names, encode -----------------------------------------------------

def track_plan(album: Album, track: Track, lex: Lexicon, leftover=None, pdf_text=None) -> dict:
    """Everything the engine needs for one track; its hash decides a rebuild."""
    template = track.intro or album.intro
    spoken = track.spoken or speak(track.title.replace(" - ", ": "), lex)
    intro = template.replace("{spoken}", spoken).replace("{title}", track.title)
    blocks = [(finish(speak(intro, lex), leftover), PAUSE["intro"],
               show(template.replace("{spoken}", track.title).replace("{title}", track.title)))]
    for part in track.parts:
        blocks += blocks_part(part, album.root, lex, leftover, pdf_text)
    blocks = [b for b in blocks if b]
    return {"version": VERSION, "engine": album.engine, "voice": album.voice, "lang": album.lang,
            "speed": album.speed, "bitrate": album.bitrate, "lead": PAUSE["lead"],
            "blocks": [[t, p] for t, p, _ in blocks], "shown": [s for _, _, s in blocks]}


def plan_sha(plan: dict) -> str:
    """Identity of the audio. The shown text is lyrics only, so it is left out:
    rewording a lyric line must not cost a re-synthesis."""
    audio = {k: v for k, v in plan.items() if k != "shown"}
    return hashlib.sha256(json.dumps(audio, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def lrc(album: Album, track: Track, shown: list, starts: list) -> str:
    """Synchronized lyrics (.lrc): one line per block at the second it starts.
    Plex and most players read the sidecar beside the track."""
    lines = [f"[ar:{album.artist}]", f"[al:{album.album}]", f"[ti:{track.title}]"]
    for text, t in zip(shown, starts):
        lines.append(f"[{int(t // 60):02d}:{t % 60:05.2f}]{text}")
    return "\n".join(lines) + "\n"


def safe_name(text: str) -> str:
    """A tag value as a file or directory name on any filesystem Plex reads."""
    return re.sub(r"\s+", " ", re.sub(r'[/\\<>:"|?*\x00-\x1f]', "-", text)).strip(" .") or "untitled"


def album_dir(out: Path, album: Album) -> Path:
    return Path(out) / safe_name(album.artist) / safe_name(album.album)


def track_file(album: Album, n: int, track: Track) -> str:
    return f"{n:0{max(2, len(str(len(album.tracks))))}d} - {safe_name(track.title)}.mp3"


def track_tags(album: Album, n: int, track: Track) -> dict:
    sources = track.comment or ", ".join(Path(p["source"]).name for p in track.parts)
    return {"title": track.title, "artist": album.artist, "album_artist": album.artist,
            "album": album.album, "date": str(album.year), "track": f"{n}/{len(album.tracks)}",
            "genre": album.genre,
            "comment": f"Source: {sources}. Synthesized voice ({album.engine.capitalize()} {album.voice})."}


def ffmpeg_cmd(audio: Path, mp3: Path, tags: dict, cover: Path | None = None,
               bitrate: str = DEFAULTS["bitrate"], copy: bool = False) -> list:
    """argv that writes one tagged MP3. ``copy`` keeps the audio stream of an
    existing MP3 and only rewrites tags and cover (no re-synthesis). ID3v2.3
    plus v1, because that pair is what every player and Plex agent reads."""
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(audio)]
    if cover:
        cmd += ["-i", str(cover)]
    cmd += ["-map", "0:a", "-map_metadata", "-1"]
    if copy:
        cmd += ["-c:a", "copy"]
    else:
        cmd += ["-filter:a", "loudnorm=I=-16:TP=-3:LRA=11", "-ar", "44100", "-ac", "1",
                "-c:a", "libmp3lame", "-b:a", bitrate]
    if cover:
        cmd += ["-map", "1:v", "-c:v", "copy", "-disposition:v", "attached_pic",
                "-metadata:s:v", "title=Album cover", "-metadata:s:v", "comment=Cover (front)"]
    cmd += ["-id3v2_version", "3", "-write_id3v1", "1"]
    for key, value in tags.items():
        cmd += ["-metadata", f"{key}={value}"]
    return cmd + ["-f", "mp3", str(mp3)]
