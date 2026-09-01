% HEE-SYNC-CURSOR-PROMPTS(1) | HEE Tools

# NAME

hee-sync-cursor-prompts - copy canonical HEE prompts into .cursor/prompts

# SYNOPSIS

    hee-sync-cursor-prompts
    hee-sync-cursor-prompts help


# DESCRIPTION


    Syncs the active HEE policy prompts into Cursor's convenience location so
    the editor reads the same text governance does. Run from a repo root.

    Source priority, first that exists wins:
      1. prompts/hee            vendored policy
      2. .hee/policy/prompts    detached policy

    Destination: .cursor/prompts

    The destination is generated state. hee-check-cursor-prompts is the
    read-only half that verifies it has not drifted.


# EXIT STATUS

    0 synced   1 no policy source found
