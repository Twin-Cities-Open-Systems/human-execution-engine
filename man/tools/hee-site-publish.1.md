% HEE-SITE-PUBLISH(1) | HEE Tools

# NAME

hee-site-publish - add files into resume/dist/ and deploy the whole tree

# SYNOPSIS

    hee-site-publish --add FILE [--add FILE ...] [--dry-run]
    hee-site-publish help


# DESCRIPTION


    Publishes to the resume Cloudflare Pages project, which serves four
    domains from one deployed tree -- spencer.blog.tcos.us,
    touchy.blog.tcos.us, blog.tcos.us and media.tcos.us -- personalized
    client-side by index.html reading window.location.hostname. There is no
    server-side routing.

    Why this tool exists: `wrangler pages deploy` is a full-tree ATOMIC
    REPLACE, not an incremental upload. Deploying a directory holding only
    new files would delete everything else already live across all four
    domains. This tool only ADDS files into a current copy of resume/dist/
    and then deploys the whole tree -- it never deploys a partial directory.

      --add       a file to add to the tree; repeatable
      --dry-run   show what would deploy, deploy nothing

    Requires a sealed Cloudflare API token at
    <resume-repo>/.hee/secrets/cloudflare-tcos-www.gpg, read via `hee-cred
    -pass`. The path is relative to the resume repo, since hee-cred's
    storage directory is CWD-relative.


# EXIT STATUS

    0 deployed (or dry-run completed)   1 usage or credential error
