% HEE-CON(1) | HEE Tools

# NAME

hee-con - connect to IRC with a real native client, persistent in tmux;

# SYNOPSIS

      hee-con -irc <channel> [-network HOST] [-session NAME] [-nick NICK]
      hee-con -tmux-send 'message' -target <session:window.pane>

    defaults:
      -network irc.libera.chat
      -session irc-<channel, # stripped>
      -nick    hee<pid>

    -tmux-send has no defaults -- -target is always required, sending into
    the wrong pane is a real footgun, not a hypothetical one.

# DESCRIPTION

    or send a real message into an existing tmux pane
