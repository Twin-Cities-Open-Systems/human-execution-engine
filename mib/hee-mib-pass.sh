#!/bin/sh
# net-snmp "pass" handler. MUST implement -n (GETNEXT) as well as -g (GET):
# snmpwalk uses GETNEXT exclusively, so a -g-only script serves single gets
# and returns nothing at all to a walk -- which looks like a broken MIB and
# is not.
OID=.1.3.6.1.4.1.66582.1.1.0
emit() { echo "$OID"; echo "string"; echo "HEE-MIB 202609062200Z"; }
case "$1" in
  -g) [ "$2" = "$OID" ] && emit ;;
  -n) case "$2" in
        .1.3.6.1.4.1.66582.1|.1.3.6.1.4.1.66582.1.1) emit ;;
        *) exit 0 ;;
      esac ;;
esac
exit 0
