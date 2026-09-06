% HEE-PRINT(1) | HEE Tools

# NAME

hee-print - render files nicely for terminal surfaces

# SYNOPSIS

    hee-print [--no-header] [--animate] [--image-format FMT] [--] FILE...
    hee-print [--no-header] --stdin [--hint md|yaml|json|text]
    SOMETHING | hee-print [--hint md|yaml|json|text]
    hee-print help


# DESCRIPTION


    Picks a renderer from the file extension, falling back to cat whenever the
    nicer tool is not installed. Never prompts, never writes.

      .md/.markdown -> glow -p
      .yml/.yaml    -> yq -P
      .json         -> jq .
      .png/.jpg/.jpeg/.gif/.webp
                    -> chafa (a still; --animate plays a GIF for 10 s), else
                       `file` plus a WARNING naming the missing renderer --
                       never a raw byte dump to the terminal
      other         -> bat/batcat -p --paging=never, else cat

    Images: the format that is known to work is the default, measured from
    where the tool is running, not guessed (operator, 2026-09-06: "when you
    find what works in tmux and not, make it the default and add a switch
    to try something else"):

      inside tmux, allow-passthrough on     -> sixels, passed through to the
                                               outer terminal (which must draw
                                               them; tmux 3.4 cannot itself)
      inside tmux, allow-passthrough off    -> symbols (pixels cannot leave tmux)
      kitty (KITTY_WINDOW_ID) / WezTerm     -> kitty
      iTerm2                                -> iterm
      Windows Terminal (WT_SESSION)         -> sixels
      anything else                         -> chafa's own guess

    --image-format FMT  try something else: symbols, sixels, kitty, iterm,
                        or auto. HEE_PRINT_IMAGE_FORMAT (heerc or environment)
                        is the same override, persistent. `--image-format
                        show` prints the format that would be used and why.

    --no-header  suppress the per-file header printed when given several files
    --animate    let an animated image play (10 s) instead of showing a still
    --stdin      read the document from stdin instead of a path. Implied when
                 no FILE is given and stdin is a pipe, so `foo | hee-print`
                 works -- answering a piped document with the usage page tells
                 the reader nothing about what went wrong
    --hint       which renderer to use when reading stdin; ignored otherwise


# EXIT STATUS

    0 rendered   2 usage error or no file given
