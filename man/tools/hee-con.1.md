% HEE-CON(1) | HEE Tools

# NAME

hee-con - connect to IRC in tmux, or send into an existing tmux pane

# SYNOPSIS

    hee-con -irc CHANNEL [-network HOST] [-session NAME] [-nick NICK]
    hee-con -tmux-send 'MESSAGE' -target SESSION:WINDOW.PANE
    hee-con help


# DESCRIPTION


    Two jobs that share a transport. The IRC side starts a real native
    client inside a persistent tmux session, so the connection survives the
    shell that started it. The -tmux-send side puts one line into a pane
    that already exists.

    IRC defaults:
      -network   irc.libera.chat
      -session   irc-<channel, # stripped>
      -nick      hee<pid>

    -tmux-send has NO defaults. -target is always required: sending into
    the wrong pane is a real footgun, not a hypothetical one.


# EXIT STATUS

    0 connected, or the message was sent
    1 unknown argument, or a required argument was missing
