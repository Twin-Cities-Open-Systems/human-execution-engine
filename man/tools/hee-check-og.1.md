% HEE-CHECK-OG(1) | HEE Tools

# NAME

hee-check-og - report the Open Graph tags a page actually serves

# SYNOPSIS

    hee-check-og URL_OR_PATH... [--raw] [--require TAG[,TAG...]] [--summary]
    hee-check-og help


# DESCRIPTION


    Fetches each URL, or reads each local file, and reports the Open Graph
    and Twitter card tags found in it. What a crawler would see, not what
    the template intended. With more than one target every report starts
    with a "== TARGET ==" line, so a sweep keeps the names (a `find | parallel
    hee check-og` sweep of 58 pages lost every name, 2026-09-06).

    --raw            print every tag as found, with no grouping or verdict
    --require TAGS   one status line per target instead of the dump:
                     OK when every named tag is present, CRITICAL naming the
                     missing ones. Default set when given bare:
                     og:title,og:description,og:url,og:image
    --summary        with --require: only the CRITICAL lines and one total


# EXIT STATUS

    0 every target read (and, with --require, complete)
    1 a target could not be read or had no tags
    2 with --require: at least one target is missing a required tag; or no target given

# EXAMPLES

    hee check-og https://tcos.us/people
    find dist -name '*.html' | xargs hee check-og --require
    hee check-og --require og:image --summary media/*/dist/**/*.html
