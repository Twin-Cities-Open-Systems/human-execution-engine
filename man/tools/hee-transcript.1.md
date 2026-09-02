% HEE-TRANSCRIPT(1) | HEE Tools

# NAME

hee-transcript - hee-transcript command

# SYNOPSIS

    hee-transcript SHARE_URL_OR_ID [-o FILE]
    hee-transcript -grep PATTERN SHARE_URL_OR_ID
    hee-transcript help


# DESCRIPTION

    hee-transcript: recover a shared ChatGPT conversation as readable text.

    Real trigger (2026-09-02): a whole family of authoring rules existed only
    in one chat log. Across every repo, `rg` for `term.kill` and `contractions
    banned` returned two hits, both code comments applying rules documented
    nowhere. Recovering that log turned up 34 named DIFs, and corrected two
    things this org had already written down wrong from memory of it.

    ## Why not WebFetch, and why not playwright

    WebFetch returns a header and a truncation notice: the visible page is
    client-rendered, so a markdown converter sees the shell and nothing else.
    Confirmed by trying it before reaching for anything heavier.

    But `curl` on the same URL returns 1.9MB of server-rendered HTML with the
    ENTIRE conversation embedded as escaped JSON. So playwright, a browser and
    a render loop are all unnecessary -- the operator suggested wiring one up,
    and the honest answer is that the cheap thing already works. Reach for a
    browser when the data is genuinely absent, not when it is merely not
    displayed.

    ## Scope, stated because it is easy to over-promise

    This reads /share/<id> URLs, which are PUBLIC. It cannot read /c/<id>
    conversation URLs -- those need the owner's session. The two ids are
    different: a conversation has to be explicitly shared to get a share id.
    So "plug in any uuid" works for anything shared, not for anything seen.


# EXIT STATUS

    0 OK        transcript recovered, or -grep found a match
    1 WARNING   -grep found nothing
    2 CRITICAL  fetch failed, or the page carried no conversation text
    3 UNKNOWN   not a share URL -- a /c/ conversation id cannot be read
