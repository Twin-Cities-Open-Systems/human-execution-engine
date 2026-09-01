% HEE-CHECK-OG(1) | HEE Tools

# NAME

hee-check-og - report the Open Graph tags a page actually serves

# SYNOPSIS

    hee-check-og URL_OR_PATH [--raw]
    hee-check-og help


# DESCRIPTION


    Fetches a URL, or reads a local file, and reports the Open Graph and
    Twitter card tags found in it. What a crawler would see, not what the
    template intended.

    --raw   print every tag as found, with no grouping or verdict


# EXIT STATUS

    0 tags found   2 no target given, or the target could not be read
