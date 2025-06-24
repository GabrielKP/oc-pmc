#!/bin/bash
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

ssh -tt $WHOST << EOF
cd word_simtype
conda activate psiturk
psiturk server on
exit
EOF
