#!/bin/sh

# a "fun" read
# https://stackoverflow.com/questions/3601515/how-to-check-if-a-variable-is-set-in-bash
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

if [[ $1 ]]
then
    WDATADIR=$2;
else
    if [[ $LV_DATA_DIR ]];
    then
        WDATADIR=$LV_DATA_DIR;
    else
        echo "LV_DATA_DIR not set, require as second argument or set in shell";
        exit 1
    fi
fi

ssh -tt $WHOST << EOF
cd linger-volition
conda activate psiturk
psiturk download_datafiles
exit
EOF
echo "Downloading data from $WHOST"

rsync $WHOST:linger-volition/*data.csv $WDATADIR/.
