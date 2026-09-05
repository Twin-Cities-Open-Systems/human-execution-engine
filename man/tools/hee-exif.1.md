% HEE-EXIF(1) | HEE Tools

# NAME

hee-exif - hee-exif command

# SYNOPSIS

    hee-exif [-h]

# DESCRIPTION

                    {read,sign,brand,provenance,gpg-sign,regen-pubkey,embed-exif}
                    ...

    positional arguments:
      {read,sign,brand,provenance,gpg-sign,regen-pubkey,embed-exif}
        read                dump all real EXIF/metadata for a file
        sign                write the real agent-instance-signature block +
                            optional Artist/Copyright
        brand               write the org's default branding: credit/publisher,
                            PEN identifier, license; Artist/Copyright defaulted
                            unless given
        provenance          write how a GENERATED image was made: tool@commit,
                            job, source (+sha256s), signed with the org rc_tag
        gpg-sign            real detached GPG signature (file.asc) -- supports
                            bulk, pass multiple files
        regen-pubkey        front-load a GPG public key from
                            github.com/<login>.gpg into a JS var in a target HTML
                            file
        embed-exif          embed real, non-blank exiftool output for every photo
                            in a dir into a JS var in a target HTML file

    options:
      -h, --help            show this help message and exit
