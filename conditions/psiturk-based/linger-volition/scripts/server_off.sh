#!/bin/bash
if [[ $1 ]]
then
    WHOST=$1;
else
    if [[ $LV_HOST ]];
    then
        WHOST=$LV_HOST;
    else
        echo "LV_HOST not set, require as first argument or set in shell";
        exit 1
    fi
fi

ssh -tt $WHOST << EOF
cd linger-volition
conda activate psiturk
psiturk server off
exit
EOF
