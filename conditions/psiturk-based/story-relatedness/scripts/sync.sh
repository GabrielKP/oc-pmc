#!/bin/bash
# input "noperm" as first arg to prevent new generation of permutations
# Author: Gabriel Kressin

DIR=/tmp/word_simtype
prev_path=$(pwd)
BRANCH="suppress-toronto"

if [[ $1 ]]
then
    WHOST=$1;
else
    if [[ $WORD_SIMTYPE_HOST ]];
    then
        WHOST=$WORD_SIMTYPE_HOST;
    else
        echo "WORD_SIMTYPE_HOST not set, require as first argument or set WORD_SIMTYPE_HOST";
        exit 1
    fi
fi

# turn server off
/bin/sh scripts/server_off.sh $1

# create temporary repo
if [[ $DIR ]]; then
    rm -rf "$DIR"
fi
git clone -b "$BRANCH" --single-branch git@github.com:GabrielKP/word_simtype.git "$DIR"
cd "$DIR"

# sync
rsync -rdvz $DIR $WHOST:.

# turn server on
/bin/sh scripts/server_on.sh $1

# back to previous path
cd "$prev_path"
