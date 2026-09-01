% HEE-PUBLISH(1) | HEE Tools

# NAME

hee-publish - 0-token activity summary, gated before it prints

# SYNOPSIS

    hee-publish -blog OPER -range "N UNIT" [-context CONTEXT]
                [--i-reviewed-manually]
    hee-publish help


# DESCRIPTION


    Renders a markdown summary of one GitHub identity's recent public
    activity to stdout. Deterministic aggregation from real recorded
    events -- no model is called at runtime, which is the point: the
    output cannot hallucinate work that did not happen.

    The source is `gh api users/OPER/events?per_page=100`: ONE page, so at
    most 100 events, and GitHub's own Events API only serves recent
    activity regardless of the range you ask for. A wide -range does not
    reach further back than the API itself does.

    Output is one heading, the since-timestamp, any notes, then one bullet
    per event, newest first:

        - **HH:MM:SS** [`owner/repo`] <what happened>

    Only six event types render -- issues, issue comments, pull requests,
    PR reviews, pushes and creates. Every other event type in the window is
    silently dropped, as is any event whose payload does not have the
    fields the renderer expects. The bullet count is therefore not the
    event count.


# OPTIONS

    -blog OPER              GitHub login whose events are read. Required.
    -range "N UNIT"         How far back. Required. Quote it -- it is one
                            argument with a space in it. UNIT is one of:
                              min  minutes
                              hrs  hours
                              day  days
                              wks  weeks
                              sess sessions -- NOT really implemented. No
                                   state-capsule lookup is wired up, so N is
                                   ignored and the window is a flat 6 hours,
                                   with a note printed in the output saying
                                   exactly that. A stated default, never a
                                   faked session boundary.
    -context CONTEXT        Free text used in the heading only. Default:
                            summary. It does not change what is collected.
    --i-reviewed-manually   Only affects the case where the content scanner
                            is unavailable: prints a loud banner to stderr
                            and publishes anyway. It cannot suppress real
                            findings.


# ENVIRONMENT

    No environment variables are read directly. `gh` must be installed and
    authenticated, and hee-filter must sit next to this script -- it is
    invoked by absolute path from this file's own directory. See
    `hee-filter help` for the cache and scanner paths it needs.


# EXIT STATUS

    Nagios plugin convention.
    0 OK        summary printed, both gates passed
    1 WARNING   a gate failed or a lookup failed -- the content scan found
                something, the scanner was unavailable without the
                override, `gh api` failed, or -range was malformed. Nothing
                is printed to stdout in any of these cases. Note: the org
                vocabulary would put several of these at 2 CRITICAL; the
                tool really exits 1 today and is documented as-is, not
                changed here.
    2 CRITICAL  argparse usage error -- -blog or -range missing


# EXAMPLES

    hee-publish -blog spencerbutler -range "6 hrs"
    hee-publish -blog spencerbutler -range "2 wks" -context "sprint recap"


# SEE ALSO

    hee-filter, contracts/publish-sanitization-v1.contract.yaml

# SAFETY

    Two gates run before a single line reaches stdout, both delegated to
    hee-filter so there is one implementation, not a copy:

    1. Repo visibility. A user's event feed includes activity in every repo
       that identity can see, private ones included. Every repo touched is
       checked live and private ones are DROPPED BEFORE RENDERING, not
       redacted after. The output states how many were excluded and names
       them -- the names are already known to whoever ran the command.
    2. Content scan. The surviving text still comes from commit messages
       and issue titles, which can themselves carry something sensitive, so
       the fully rendered output is scanned before printing. If the scanner
       is unavailable this tool prints NOTHING and fails rather than
       skipping the scan silently.
