% HEE-SSH-SEND-KEYS(8) | HEE Tools

# NAME

hee-ssh-send-keys - hee-ssh-send-keys command

# SYNOPSIS

    hee-ssh-send-keys [-h] [-source SOURCE] [-dest DEST] [--generate]

# DESCRIPTION

                             [--validity VALIDITY] [--gpg-key GPG_KEY]
                             [--key-path KEY_PATH]

    options:
      -h, --help           show this help message and exit
      -source SOURCE
      -dest DEST
      --generate
      --validity VALIDITY
      --gpg-key GPG_KEY    GPG key to sign the receipt with
      --key-path KEY_PATH


# EXAMPLES

    hee ssh-send-keys -source claude@flippy -dest agent@pve --generate

    Not marked "# ci": it reaches two hosts over ssh and installs keys, which a
    runner cannot do.
