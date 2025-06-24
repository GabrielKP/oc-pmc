#!/bin/sh
# Author: Gabriel Kressin

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

/bin/sh scripts/server_off.sh $WHOST

rsync -rv\
    --exclude=.git\
    --exclude="data*"\
    --exclude=trialdata.csv\
    --exclude=questiondata.csv\
    --exclude=eventdata.csv\
    --exclude=participants.db\
    --exclude=.psiturk_history\
    --exclude=server.log\
    --delete\
    $(pwd)/ $WHOST:~/linger-volition

/bin/sh scripts/server_on.sh $WHOST
