use strict;
use warnings;
use Irssi;
use HTTP::Tiny;
use JSON::PP;

# hee_qdb.pl -- real /QDB command, native to irssi.
#
# Real trigger (2026-08-24): "/qdb that shit in irc... not central, is
# chaos entropy tool too" (tooling/bin/hee-qdb, PR#283) -- this is the
# irssi-native front end for it. Design discussion same session started
# from a proposed filename-encoding scheme
# (~/<path>/qdb/attrib-details-....qdb), reasoned away from it after
# real footguns: this host's actual filename limit (getconf NAME_MAX)
# is 255 bytes, quotes routinely contain "/" and multi-line text which
# are illegal/broken in filename components, and slugifying is lossy.
# Spencer's own pivot: "keep in some repo and feed to api endpoint
# somewhere and can be used in irssi" -- this file is that irssi half.
#
# Same shape as hee_finger.pl (this directory) -- a real HTTP call, not
# a local shell-out, so /QDB works from any irssi instance regardless
# of local repo access. Uses HTTP::Tiny + JSON::PP -- both core Perl,
# no extra CPAN deps, matching hee's own minimalism.
#
# Real, known dependency, not yet live: hits tcos.us/api/quotes, which
# is designed (fleet-ops#266) but not yet deployed -- blocked on the
# same missing Cloudflare token as human-execution-engine#319. This
# script is real and correct against that intended contract; it will
# return a real connection-failure message until that endpoint exists,
# not a silent no-op.
#
# usage inside irssi:
#   /QDB                  -- random quote, no filter
#   /QDB counting fact     -- search term

our $VERSION = "1.0";
our %IRSSI = (
    authors     => "touchy-claude",
    contact     => "hee-irc\@tcos.us",
    name        => "hee_qdb",
    description => "Real /QDB command -- fetches a real quote from tcos.us/api/quotes.",
    license     => "MIT",
);

my $API_URL = "https://tcos.us/api/quotes";

sub cmd_qdb {
    my ($query, $server, $witem) = @_;
    $query =~ s/^\s+|\s+$//g;

    my $url = $API_URL;
    if ($query ne "") {
        my $encoded = $query;
        $encoded =~ s/([^A-Za-z0-9._~-])/sprintf("%%%02X", ord($1))/ge;
        $url .= "?search=$encoded";
    }

    my $http = HTTP::Tiny->new(timeout => 10);
    my $resp = $http->get($url);

    unless ($resp->{success}) {
        Irssi::active_win()->print(
            "hee_qdb: request failed ($resp->{status} $resp->{reason}) -- "
            . "is the /api/quotes endpoint deployed yet? (fleet-ops#266)"
        );
        return;
    }

    my $data;
    eval { $data = decode_json($resp->{content}); 1 }
        or do {
            Irssi::active_win()->print("hee_qdb: bad JSON from server: $@");
            return;
        };

    unless (ref $data eq 'HASH' && $data->{quote}) {
        Irssi::active_win()->print("hee_qdb: no match" . ($query ne "" ? " for '$query'" : ""));
        return;
    }

    my $speaker = $data->{speaker} // "unknown";
    my $date    = $data->{date} // "";
    my $quote   = $data->{quote};

    Irssi::active_win()->print("qdb: \"$quote\" -- $speaker" . ($date ne "" ? " ($date)" : ""));
}

Irssi::command_bind("qdb", \&cmd_qdb);
