#!/bin/bash 
# Drive command line utilities
USER="$(cat .mtuser)"
PASS="$(cat .mtpass)"
ICAL="$(cat .mtical)"

case $1 in
    download)
        shift;
        ./download.py --user $USER --pass "$PASS" --ical "$ICAL" "$@"
        ;;
    *)
        shift;
        ./summary.py --user $USER --pass "$PASS" --ical "$ICAL" "$@"
        ;;
esac;
