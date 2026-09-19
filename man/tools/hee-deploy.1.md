% HEE-DEPLOY(1) | HEE Tools

# NAME

hee-deploy - publish a directory of markdown + images as a resume blog post

# SYNOPSIS

    hee deploy blog [DIR] [-oper SLUG] [-to lab|prod] [-dry-run] [-no-pr] [-resume PATH]
    hee deploy help | blog help


# DESCRIPTION


      Turns a directory shaped like:

        mkdir my-new-blog && cd my-new-blog
        echo "# Title of new blog" > blog.md
        cp /some/path/images* .
        ls {a,b,c,d}.png
        ls {a,b,c,d}.png.md        # notes, stories or info about each image
        hee deploy blog -to lab    # warn on a title-only post, but deploy it for testing

      into a real post on the resume checkout at `-resume` (default
      `~/git/resume`): a branch `blog/<oper>-<slug>` off `origin/main`,
      `profiles/<oper>/blog/<slug>.md` plus its images copied beside it, built
      with `./convert.sh`, pushed to lab with `media/bin/deploy.sh <oper> lab`,
      and a PR that records what is already live. DIR defaults to `.`.

      DIR is the unit of input:

        blog.md               line 1 `# Title` (required); line 2 may be
                               `**Date:** YYYY-MM-DD`; then prose. Markdown
                               only, no raw HTML.
        *.png *.jpg *.jpeg
        *.gif *.webp           figures, in byte-order filename sort
        <image>.md             the note for that image (e.g. `a.png.md` notes
                               `a.png`); its first non-empty line is the
                               figure's alt text, the rest is the caption

      The slug is DIR's basename, lowercased; it must match
      `^[a-z0-9][a-z0-9-]*$` or the tool refuses. The oper is `-oper` if given,
      else `$USER` when that is a profile under `<resume>/profiles/`, else the
      tool refuses and lists the profiles it found -- it never guesses a
      person.

      -oper       which person's blog; default: $USER if it is a profile
      -to         lab|prod, default lab. prod (phase 1) only prints the
                  release procedure and does nothing else.
      -dry-run    run every gate, print the assembled post between
                  `----- post -----` markers and the files that would be
                  written, write nothing, create no branch, run nothing
      -no-pr      leave the branch local after deploying to lab, no PR
      -resume     path to the resume checkout, default ~/git/resume

    GATES (in order, each with its exit code)
      DIR missing, or no blog.md, or line 1 not '# Title'    CRITICAL 2, refuse
      slug not slug-safe                                     CRITICAL 2, refuse
      -oper not a profile dir with profile.json              CRITICAL 2, refuse, lists profiles
      an <image>.md note whose image is absent               CRITICAL 2, refuse
      blog.md has a title and no other non-empty line        WARNING 1 on lab (deploys anyway),
                                                              CRITICAL 2 on prod (refuse)
      an image with no note                                  WARNING 1, deploys anyway
      -to prod                                                UNKNOWN 3, prints the release
                                                              procedure, does nothing


# EXIT STATUS

      0  OK -- deployed (or dry-run completed) clean
      1  WARNING -- deployed (or dry-run completed) anyway
      2  CRITICAL -- refused; nothing written, nothing deployed
      3  UNKNOWN -- -to prod: printed the release procedure, did nothing else

    NOT IN V1
      media and meme kinds, -to prod beyond printing the procedure, editing an
      existing post, deleting images.


# EXAMPLES

    hee deploy blog ./my-new-blog -dry-run
    hee deploy blog ./my-new-blog -oper alice -to lab
    hee deploy blog ./my-new-blog -to prod
    hee deploy help
