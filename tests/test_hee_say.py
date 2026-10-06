"""hee say -- text becomes what a speech engine says correctly, an album is a hee object.

Nothing here synthesizes audio: the engine and its 350 MB model are not on a
runner. What is tested is everything that decides WHAT is said and how the
files are named and tagged, plus the CLI paths that must work with no engine
(script, check, card, build --dry-run) by pointing HEE_SAY_HOME at an empty
directory.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tooling" / "bin" / "hee-say"
FIX = ROOT / "tests" / "fixtures" / "say"
CARD = FIX / "field-notes.card.v1.yaml"
sys.path.insert(0, str(ROOT / "library" / "py"))
import hee_say as S


def lexicon(**spec):
    lex = S.Lexicon()
    lex.merge_object({"apiVersion": "hee/v1", "kind": "Registry",
                      "metadata": {"labels": {"artifact": "say-lexicon"}}, "spec": spec})
    return lex


def run(*args, home=None):
    env = dict(os.environ, HEE_STATUS_STYLE="plain", HEE_SAY_HOME=home or tempfile.mkdtemp())
    env.pop("HEE_SAY_ARTIST", None)
    env.pop("HEE_SAY_OUT", None)
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=env, cwd=ROOT)


class Speak(unittest.TestCase):
    def test_acronyms_are_hyphenated_never_spaced(self):
        # "A P R S" is read "uh P R S"; the hyphens are the fix
        lex = lexicon(acronyms=["APRS", "LED"])
        self.assertEqual(S.speak("APRS and LEDs", lex), "A-P-R-S and L-E-D's")

    def test_an_a_after_the_first_letter_is_written_eigh(self):
        # "Q-A-M" is read "Q uh M" and "F-A-A" "F uh uh" (measured 2026-10-05)
        lex = lexicon(acronyms=["QAM", "FAA", "TDMA", "APRS"],
                      rules=[{"match": r"\b[KW][A-Z]?\d[A-Z]{1,3}\b", "spell": "letters"}])
        self.assertEqual(S.speak("QAM FAA TDMA APRS", lex), "Q-Eigh-M F-Eigh-Eigh T-D-M-Eigh A-P-R-S")
        self.assertEqual(S.speak("WA1AA", lex), "W-Eigh one A-Eigh")

    def test_longer_acronym_wins_over_its_prefix(self):
        lex = lexicon(acronyms=["SS", "SSB"])
        self.assertEqual(S.speak("SSB", lex), "S-S-B")

    def test_decimal_point_is_spoken(self):
        self.assertEqual(S.speak("144.39 and 441.025", S.Lexicon()), "144 point 3 9 and 441 point 0 2 5")

    def test_version_and_address_are_not_decimals(self):
        self.assertEqual(S.speak("10.0.0.72 v5.2.3", S.Lexicon()), "10.0.0.72 v5.2.3")

    def test_symbols_links_and_marks(self):
        said = S.speak("**A** → `B` / C — see [the guide](https://x.example/g), https://tcos.us/x", S.Lexicon())
        self.assertEqual(said, "A, to B or C, see the guide, tcos dot us")

    def test_callsign_letters_keep_digits_as_separate_words(self):
        # one hyphen chain ("W-one-A-W") makes the engine read the A as "uh"
        lex = lexicon(rules=[{"match": r"\b[KW]\d[A-Z]{1,3}\b", "spell": "letters"},
                             {"match": r"\b\d{6}\b", "spell": "digits"}])
        self.assertEqual(S.speak("W1AW on node 629272", lex), "W one A-W on node 6 2 9 2 7 2")

    def test_rules_run_in_order_on_raw_text(self):
        lex = lexicon(rules=[{"match": r"\*3 (\d)", "say": r"star 3, \1"}, {"match": r"\bMHz\b", "say": "megahertz"}])
        self.assertEqual(S.speak("dial *3 5 on 146 MHz", lex), "dial star 3, 5 on 146 megahertz")

    def test_lexicon_symbol_overrides_builtin(self):
        self.assertEqual(S.speak("a / b", lexicon(symbols={"/": " slash "})), "a slash b")

    def test_finish(self):
        left = set()
        self.assertEqual(S.finish("THAT DOT came from W3,", left), "that dot came from W3.")
        self.assertEqual(S.finish("Really?"), "Really?")
        self.assertEqual(S.finish("It is done.."), "It is done.")
        self.assertEqual(S.unpronounceable(left), ["W3"])
        self.assertEqual(S.unpronounceable({"THE", "CTCSS", "PL259"}), ["CTCSS", "PL259"])

    def test_bad_lexicon_is_refused(self):
        for spec in ({"rules": [{"match": "(", "say": "x"}]}, {"rules": [{"match": "a"}]},
                     {"rules": [{"match": "a", "spell": "words"}]}, {"acronyms": ["lower"]}):
            with self.assertRaises(S.SayError, msg=spec):
                lexicon(**spec)


class Blocks(unittest.TestCase):
    def test_markdown(self):
        md = (FIX / "notes" / "01-receiving.md").read_text()
        blocks = S.blocks_markdown(md, S.load_lexicon([FIX / "field.say-lexicon.registry.v1.yaml"]),
                                   {"drop": ["^Status:"]})
        said = [b[0] for b in blocks]
        self.assertEqual(said[0], "The path.")                       # H1 and the Status line are gone
        self.assertIn("antenna, to S-D-R, to decoder, to map or data.", said)
        self.assertIn("2: Watch for W one A-W and node 1 2 3 4 5 6.", said)
        self.assertFalse(any("never read aloud" in s for s in said))  # fenced code
        self.assertEqual(said[-1], "See the guide for more.")
        shown = [b[2] for b in blocks]
        self.assertIn("2. Watch for W1AW and node 123456.", shown)   # lyrics keep the source's words
        self.assertIn("ANTENNA → SDR → DECODER → MAP / DATA", shown)

    def test_markdown_rewrite_and_kept_h1(self):
        blocks = S.blocks_markdown("# Title\n\n**Authority:** check it\n", S.Lexicon(),
                                   {"skip_h1": False, "rewrite": [{"match": r"^\*\*Authority:\*\*\s*", "say": "Note: "}]})
        self.assertEqual([b[0] for b in blocks], ["Title.", "Note: check it."])

    def test_markdown_comments_say_nothing_even_across_lines(self):
        md = "One. <!-- hidden -->\n\n<!-- a comment\nover two lines -->\nTwo.\n\n<!-- never closed\nThree.\n"
        self.assertEqual([b[0] for b in S.blocks_markdown(md, S.Lexicon())], ["One.", "Two."])

    def test_records(self):
        data = yaml.safe_load((FIX / "facts.yaml").read_text())
        opts = {"items": "facts", "where": {"group": "A"}, "group_by": "group", "group_heading": "Group {group}.",
                "say": [{"when": "answers", "say": "{question} {answers}."}, {"say": "{question} {answer}."}]}
        said = [b[0] for b in S.blocks_records(data, S.Lexicon(), opts)]
        self.assertEqual(said, ["Group A.", "What does an sdr do? It turns rf into numbers.",
                                "Which of these blink? LEDs; Beacons."])

    def test_records_where_null_and_missing_field(self):
        data = {"q": [{"t": "one", "fig": None}, {"t": "two", "fig": "F1"}]}
        said = S.blocks_records(data, S.Lexicon(), {"items": "q", "where": {"fig": None}, "say": "{t}"})
        self.assertEqual([b[0] for b in said], ["one."])
        with self.assertRaises(S.SayError):
            S.blocks_records(data, S.Lexicon(), {"items": "q", "say": "{nope}"})

    def test_pdf_text_needs_named_paragraphs(self):
        text = "Summary - Talk\nFirst part runs\non. Second part\nends."
        opts = {"skip_prefix": "Summary - Talk", "paragraphs": ["Second part"]}
        self.assertEqual([b[0] for b in S.blocks_pdf_text(text, S.Lexicon(), opts)],
                         ["First part runs on.", "Second part ends."])
        with self.assertRaises(S.SayError):
            S.blocks_pdf_text(text, S.Lexicon(), {"paragraphs": ["Not there"]})

    def test_pdf_source_without_engine_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.pdf").write_bytes(b"%PDF-1.4")
            with self.assertRaises(S.SayError):
                S.blocks_part({"source": "a.pdf"}, Path(d), S.Lexicon())


class Albums(unittest.TestCase):
    def test_card_loads_with_defaults_merged(self):
        album = S.load_card(CARD)
        self.assertEqual((album.artist, album.album, album.year, album.voice), ("Field Notes", "Field Notes - 2026", 2026, "af_heart"))
        self.assertEqual([t.title for t in album.tracks], ["Receiving a Signal", "Antennas", "Quick Facts"])
        self.assertEqual(album.tracks[0].parts[0]["drop"], ["^Status:"])
        self.assertEqual(album.genre, "Speech")
        self.assertEqual(album.bitrate, "64k")

    def test_bad_cards_are_refused(self):
        good = yaml.safe_load(CARD.read_text())
        for breakit in (lambda o: o.update(kind="Pill"), lambda o: o["metadata"]["labels"].pop("artifact"),
                        lambda o: o["spec"].pop("artist"), lambda o: o["spec"]["tracks"][0].pop("title"),
                        lambda o: o["spec"]["tracks"][0].update(parts=[{"heading": "no source"}])):
            obj = json.loads(json.dumps(good))
            breakit(obj)
            with tempfile.NamedTemporaryFile("w", suffix=".yaml") as fh:
                yaml.safe_dump(obj, fh)
                fh.flush()
                with self.assertRaises(S.SayError):
                    S.load_card(fh.name)

    def test_plan_is_the_spoken_script_and_its_hash_ignores_lyrics(self):
        album = S.load_card(CARD)
        lex = S.load_lexicon(album.lexicons)
        plan = S.track_plan(album, album.tracks[1], lex)
        self.assertEqual(plan["blocks"][0], ["Field Notes. Antennas, briefly.", S.PAUSE["intro"]])
        self.assertEqual(plan["shown"][0], "Field Notes. Antennas.")
        self.assertEqual(plan["blocks"][-1][0], "Height matters more than length, put it up high.")
        sha = S.plan_sha(plan)
        self.assertEqual(sha, S.plan_sha(dict(plan, shown=["reworded"])))
        self.assertNotEqual(sha, S.plan_sha(dict(plan, voice="am_michael")))

    def test_loose_sources_make_the_same_album_shape(self):
        os.environ.pop("HEE_SAY_ARTIST", None)
        album = S.album_from_sources([FIX / "notes"], year=2026)
        self.assertEqual([t.title for t in album.tracks], ["Receiving a Signal", "Antennas"])
        self.assertEqual((album.artist, album.album), ("Unknown Artist", "notes"))
        obj = S.card_object(album.override(artist="Field Notes"))
        self.assertEqual(obj["metadata"]["annotations"], {"inuid": None, "inuid_null_reason": "soa_pending"})
        with tempfile.TemporaryDirectory() as d:
            card = Path(d) / "a.card.v1.yaml"
            card.write_text(yaml.safe_dump(obj, sort_keys=False))
            self.assertTrue(S.is_album_card(card))
            again = S.load_card(card, src=album.root)
        self.assertEqual([t.title for t in again.tracks], [t.title for t in album.tracks])
        with self.assertRaises(S.SayError):
            S.album_from_sources([FIX / "no-such-dir"])

    def test_names_and_tags(self):
        album = S.load_card(CARD)
        self.assertEqual(S.track_file(album, 2, album.tracks[1]), "02 - Antennas.mp3")
        self.assertEqual(S.safe_name('AC/DC: "Live"?'), "AC-DC- -Live--")
        self.assertEqual(S.album_dir(Path("/out"), album), Path("/out/Field Notes/Field Notes - 2026"))
        tags = S.track_tags(album, 1, album.tracks[0])
        self.assertEqual(tags["track"], "1/3")
        self.assertEqual(tags["album_artist"], "Field Notes")
        self.assertEqual(tags["comment"], "Source: notes/01-receiving.md. Synthesized voice (Kokoro af_heart).")

    def test_ffmpeg_argv(self):
        tags = {"title": "T"}
        enc = S.ffmpeg_cmd(Path("a.wav"), Path("a.mp3"), tags, Path("c.jpg"), "64k")
        self.assertIn("loudnorm=I=-16:TP=-3:LRA=11", enc)
        self.assertEqual(enc[enc.index("-id3v2_version") + 1], "3")
        self.assertIn("attached_pic", enc)
        self.assertIn("title=T", enc)
        copy = S.ffmpeg_cmd(Path("a.mp3"), Path("b.mp3"), tags, copy=True)
        self.assertIn("copy", copy)
        self.assertNotIn("libmp3lame", copy)
        self.assertNotIn("attached_pic", copy)

    def test_lrc(self):
        album = S.load_card(CARD)
        text = S.lrc(album, album.tracks[0], ["one", "two"], [0.4, 65.129])
        self.assertEqual(text.splitlines(), ["[ar:Field Notes]", "[al:Field Notes - 2026]",
                                             "[ti:Receiving a Signal]", "[00:00.40]one", "[01:05.13]two"])


class Cli(unittest.TestCase):
    def test_script_and_check_need_no_engine(self):
        r = run("script", str(CARD))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("===== 03 - Quick Facts.mp3", r.stdout)
        self.assertIn("Which of these blink? All of these: L-E-D's; Beacons.", r.stdout)
        r = run("check", str(CARD))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("OK Field Notes / Field Notes - 2026 (2026): 3 tracks", r.stdout)

    def test_loose_text_without_an_artist_warns(self):
        r = run("check", str(FIX / "notes"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("no artist named", r.stderr)

    def test_dry_run_plans_and_real_build_refuses_without_engine(self):
        with tempfile.TemporaryDirectory() as out:
            r = run("build", str(CARD), "--out", out, "--dry-run")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.count("synthesize"), 3)
            self.assertEqual(os.listdir(out), [])               # a dry run writes nothing
            r = run("build", str(CARD), "--out", out, "--only", "1")
            self.assertEqual(r.returncode, 3)
            self.assertIn("hee say setup", r.stderr)

    def test_options_override_the_card(self):
        r = run("card", str(CARD), "--voice", "am_michael", "--artist", "Someone Else")
        obj = yaml.safe_load(r.stdout)
        self.assertEqual(obj["spec"]["voice"]["name"], "am_michael")
        self.assertEqual(obj["spec"]["artist"], "Someone Else")

    def test_exit_codes(self):
        self.assertEqual(run("build").returncode, 3)                         # usage
        self.assertEqual(run("script", "no-such-file.md").returncode, 2)     # missing source
        self.assertEqual(run("script", str(CARD), "--only", "9").returncode, 2)
        self.assertEqual(run("setup", "--check").returncode, 1)              # empty HEE_SAY_HOME

    def test_help_from_anywhere_runs_nothing(self):
        with tempfile.TemporaryDirectory() as out:
            r = run("build", str(CARD), "--out", out, "help")
            self.assertEqual(r.returncode, 0)
            self.assertIn("SYNOPSIS", r.stdout)
            self.assertEqual(os.listdir(out), [])


if __name__ == "__main__":
    unittest.main()
