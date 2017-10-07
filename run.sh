#!/bin/bash 
# Drive command line utilities
set -euf -o pipefail

USER="$(cat .mtuser)"
PASS="$(cat .mtpass)"
ICAL="$(cat .mtical)"

if [ "$#" == "0" ]; then
    echo "Usage: 
            $0 download             Download event resources
            $0 summary              Create summary pages for given date
    "
    exit 1
fi

case "$1" in
    download)
        shift;
        ./download.py --user $USER --pass "$PASS" --ical "$ICAL" "$@"
        ;;
    summary)
        shift;
        ./summary.py --user $USER --pass "$PASS" --ical "$ICAL" "$@"
        ;;

    *)
        echo "Usage: $0 (download|summary)"
        echo
esac;
