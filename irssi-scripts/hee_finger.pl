use strict;
use warnings;
use Irssi;
use IO::Socket::INET;

# hee_finger.pl -- real /FINGER command, native to irssi.
#
# Real trigger (2026-08-22): "we imp finger in custom irssi plugin,"
# then "I hate perl, it is a must for hee. yes perl is way hee use
# it" -- irssi's real scripting language is Perl, so a native command
# means Perl, not a workaround. This file exists to prove Perl can be
# written clearly, not to prove a point about Perl itself.
#
# Same protocol logic as tooling/bin/hee-net's -proto finger in
# human-execution-engine (RFC 1288: connect to port 79, send the
# query + CRLF, read plaintext back) -- kept in sync by hand for now,
# not shared code, since irssi scripts and standalone Python tools
# don't share a runtime.
#
# usage inside irssi:
#   /FINGER spencer                  -- local account (shells to real finger(1))
#   /FINGER spencer@some.host        -- remote, real RFC 1288 socket query
#   /FINGER spencer@some.host:7979   -- remote, custom port

our $VERSION = "1.0";
our %IRSSI = (
    authors     => "touchy-claude",
    contact     => "hee-irc\@tcos.us",
    name        => "hee_finger",
    description => "Real /FINGER command -- local shells to finger(1), remote speaks RFC 1288 directly.",
    license     => "MIT",
);

sub cmd_finger {
    # irssi hands command handlers: (raw args string, active server, active witem)
    my ($query, $server, $witem) = @_;
    $query =~ s/^\s+|\s+$//g;  # trim -- irssi doesn't do this for us

    if ($query eq "") {
        Irssi::active_win()->print("hee_finger: usage: /FINGER user[\@host[:port]]");
        return;
    }

    my $result;
    if ($query =~ /^([^@]+)@([^:]+)(?::(\d+))?$/) {
        # remote -- real socket, real protocol, no shelling out
        my ($user, $host, $port) = ($1, $2, $3 // 79);
        $result = finger_remote($user, $host, $port);
    } else {
        # local -- real finger(1) already handles .plan/sessions correctly
        $result = `finger $query 2>&1`;
    }

    # print each real line into the active window -- one /FINGER call,
    # one real block of output, no truncation
    for my $line (split /\n/, $result) {
        Irssi::active_win()->print("finger: $line");
    }
}

sub finger_remote {
    my ($user, $host, $port) = @_;

    my $sock = IO::Socket::INET->new(
        PeerAddr => $host,
        PeerPort => $port,
        Proto    => "tcp",
        Timeout  => 10,
    );
    return "connection to $host:$port failed: $!" unless $sock;

    print $sock "$user\r\n";

    local $/;  # slurp mode -- read the whole real response, not line by line
    my $response = <$sock>;
    close $sock;

    return defined $response ? $response : "(no response)";
}

Irssi::command_bind("finger", \&cmd_finger);
