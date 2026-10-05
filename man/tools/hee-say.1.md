% HEE-SAY(1) | HEE Tools

# NAME

hee-say - read text aloud into a tagged MP3 album, with cover and lyrics

# SYNOPSIS

    hee-say build SOURCE... [ALBUM OPTIONS] [--out DIR] [--only N] [--force] [--dry-run]
    hee-say script SOURCE... [ALBUM OPTIONS] [--only N] [--shown]
    hee-say check SOURCE... [ALBUM OPTIONS]
    hee-say card SOURCE... [ALBUM OPTIONS]
    hee-say phonemes [--lexicon FILE]... TEXT...
    hee-say voices
    hee-say setup [--check]
    hee-say [VERB] help

    ALBUM OPTIONS
      --artist NAME   --album NAME   --year YYYY   --genre NAME
      --voice NAME    --speed N      --lang CODE   --bitrate RATE
      --cover IMAGE   --lexicon FILE (repeatable)  --src DIR


# DESCRIPTION


    Point it at text and it writes an album: one MP3 per source, tagged, with
    the cover embedded and the words as timed lyrics. Speech is synthesized on
    this machine by Kokoro, an open model that runs on a CPU; nothing is sent
    anywhere and nothing is billed.

    SOURCE is either text -- files or directories of .md, .markdown, .txt and
    .pdf, one track per file, a directory's files in name order -- or ONE album
    object: a hee/v1 Card with labels.artifact: say-album, which names the
    artist, the album, every track and where each track's words come from.
    Loose text and a Card build the same way; `hee say card` prints the Card for
    whatever you pointed it at, so an ad hoc album becomes a committed one by
    saving that output (its sources are written relative to the directory you
    ran it in: save it there, or build it with --src).

    Defaults, when neither the Card nor an option says otherwise: voice
    af_heart at speed 1.0, 64 kbit/s mono MP3 at one loudness (-16 LUFS), ID3
    v2.3 tags, genre Speech, this year, the album named after the source
    directory, and tracks named "NN - Title.mp3" under DIR/Artist/Album/.

    An agent cannot listen to what it makes. `script` prints exactly what will
    be said, `check` lists the upper-case tokens no rule covers, and `phonemes`
    shows how the engine will pronounce a phrase. Read those instead.


# ENVIRONMENT

    HEE_SAY_OUT     where albums go (default ~/.hee/say); --out wins
    HEE_SAY_ARTIST  the artist for loose text when --artist is not given
    HEE_SAY_HOME    the engine's venv and model
                    (default ${XDG_DATA_HOME:-~/.local/share}/hee/say)


# EXIT STATUS

    0 OK   1 WARNING (check found tokens no rule covers, or no artist was named)
    2 CRITICAL (a bad album object, a missing source, the engine or ffmpeg failed)
    3 UNKNOWN (usage, or the engine is not installed: run hee say setup)


# EXAMPLES

    $ hee say script tests/fixtures/say/field-notes.card.v1.yaml   # ci
    $ hee say check tests/fixtures/say/field-notes.card.v1.yaml   # ci
    $ hee say card tests/fixtures/say/notes --artist "Field Notes" --year 2026   # ci
    $ hee say build tests/fixtures/say/field-notes.card.v1.yaml --out "$(mktemp -d)" --dry-run   # ci
    $ hee say build ~/notes --artist "Field Notes" --voice am_michael --out /srv/music
    $ hee say phonemes --lexicon ham.say-lexicon.registry.v1.yaml "APRS on 144.39 MHz"
    $ hee say setup

    The last three are not marked "# ci": they need the speech engine and its
    350 MB model, which a bare runner does not carry.

# VERBS

    build     synthesize, encode and tag. A track is re-synthesized only when
              its spoken text, voice or encoding changed; a changed tag, cover
              or lyric line is rewritten without touching the audio; an
              unchanged track is left alone. --force rebuilds everything,
              --only N builds one track, --dry-run says what would happen and
              needs no engine.
    script    print each track's spoken text, one block per line. --shown
              prints the lyric text instead (the source's own wording).
    check     validate the album and its sources and count what would be said.
              Upper-case tokens with no vowel or with a digit, which no rule
              covers, are a WARNING; short upper-case words are listed for a
              reader to judge.
    card      print the album as a hee/v1 Card.
    phonemes  print each TEXT as it would be spoken, then the engine's
              phonemes for it. --lexicon applies a pronunciation lexicon first.
    voices    list the engine's voices.
    setup     create the engine's venv and fetch its model (about 350 MB, one
              time). --check reports what is installed and changes nothing.


# OBJECTS

    An album (labels.artifact: say-album). Lexicon and cover paths are relative
    to the Card; a part's source is relative to --src when given, else to the
    Card.

      apiVersion: hee/v1
      kind: Card
      metadata:
        name: say-field-notes
        labels: {hee.object: "true", artifact: say-album}
        annotations: {inuid: null, inuid_null_reason: soa_pending}
      spec:
        artist: Field Notes
        album: "Field Notes - 2026"
        year: 2026
        voice: {name: af_heart, speed: 1.0}     # optional, as are genre, bitrate
        lexicon: [field.say-lexicon.registry.v1.yaml]
        cover: cover.jpg
        intro: "Field Notes. {spoken}."         # said first on every track
        defaults: {drop: ['^Status:']}          # merged into every part
        tracks:
          - title: Receiving
            spoken: Receiving a signal          # how the intro says the title
            comment: receiving.md, revision B   # goes in the comment tag
            parts:
              - source: receiving.md

    A part reads one file. Its format follows the file name unless `format`
    says markdown, text, pdf or records. Any part may carry `heading` (said
    before it), `drop` (regexes; a matching line is skipped) and `rewrite`
    ({match, say} pairs applied to each line). A pdf part may name
    `paragraphs` (each paragraph's opening words, since PDF text carries no
    paragraph marks) and `skip_prefix`. A records part reads a YAML or JSON
    list: `items` (dotted path to the list), `where` ({field: value}) and
    `say`, a template such as "{question} {answer}" or a list of
    {when: FIELD, say: TEMPLATE} tried in order. `group_by` (a field) with
    `group_heading` (a template) says a heading whenever that field changes.

    A lexicon (labels.artifact: say-lexicon) is a hee/v1 Registry:

      spec:
        acronyms: [SDR, LED]                    # said letter by letter
        rules:                                  # regex, in order, on raw text
          - {match: '\bMHz\b', say: megahertz}
          - {match: '\b[KNW]\d[A-Z]{1,3}\b', spell: letters}
          - {match: '\b\d{6}\b', spell: digits}
        symbols: {"/": " or "}                  # overrides a built-in symbol


# OUTPUT

    DIR/Artist/Album/NN - Title.mp3   the track, cover embedded
    DIR/Artist/Album/NN - Title.lrc   its lyrics, timed line by line
    DIR/Artist/Album/cover.jpg        the cover, for players that read a file
    DIR/Artist/Album/.hee-say.json    what each track was built from
