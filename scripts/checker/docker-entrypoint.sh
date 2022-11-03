#!/usr/bin/env bash

usage() {
    echo "usage: $0 --service SERVICE --checkerscript CHECKERSCRIPT
                    [--ippattern IPPATTERN --flagsecret FLAGSECRET] 
                    [--checkercount CHECKERCOUNT --interval INTERVAL]
                    [IP TICK TEAM]"
}

ARGS=("$@")
in_args () {
    for V in "${ARGS[@]}"; do
        if [[ "$1" == "$V" ]]; then
            return 0
        fi
    done
    return 1
}

for arg in service checkerscript; do
    envar="CTF_${arg^^}"
    in_args "--${arg}" || [[ "x${!envar}" != "x" ]] || {
        usage
        exit 1
    }
done

[[ "x$CTF_CHECKERSCRIPT" != "x" ]] || {
    echo "<!> undefined environment variable 'CTF_CHECKERSCRIPT'"
    exit 1
}

for arg in ippattern flagsecret checkercount interval; do
    envar="CTF_${arg^^}"
    in_args "--${arg}" || [[ "x${!envar}" != "x" ]] || {
        SCRIPT="$CTF_CHECKERSCRIPT"
        unset CTF_CHECKERSCRIPT
        exec "$SCRIPT" $@
    }
done

exec ctf-checkermaster $@
