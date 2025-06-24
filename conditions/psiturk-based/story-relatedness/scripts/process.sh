#!/bin/bash

if [ -z "$1" ]
then
    echo "require experiment dir.";
    exit 1
fi
EXP_DIR=$1;

python analysis/extract_data.py -s $EXP_DIR
python plot/overview.py -s $EXP_DIR
python analysis/overview.py -s $EXP_DIR

mkdir $EXP_DIR/zipfiles
cd $EXP_DIR/plots/overview
zip plots.zip ./*
cd ../../../
mv $EXP_DIR/plots/overview/plots.zip $EXP_DIR/zipfiles/

cd $EXP_DIR/outputs
zip ratings.zip ./*
cd ../../
mv $EXP_DIR/outputs/ratings.zip $EXP_DIR/zipfiles/
