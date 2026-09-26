% HEE-PROCMAIL(1) | HEE Tools

# NAME

hee-procmail - hee-procmail command

# SYNOPSIS

    hee-procmail [-h] [-rules PATH]

# DESCRIPTION

    options:
      -h, --help   show this help message and exit
      -rules PATH


# EXAMPLES

    cat message.eml | hee procmail

    Not marked "# ci": it filters a message on stdin against the rule file at
    .hee/mailrules.yaml, which is operator mail config, not a repo fixture.
