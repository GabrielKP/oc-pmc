# linger-volition

How much do participants have to think about a recent experience story, even when told not to?

In this online experiment, participants are following the paradigm from Bellana et al. 2022 closely:

1. Free association (pre) - 3mins
2. Story reading
3. Free association (post) - 3mins
4. Questionnaires

During free association participants are told not to think about a certain topic. In the pre-story free association this is 'food' in the post-story free association it is the story. Additionally, participants are instructed to press a button, whenever they think about food/the story.

This repository implements 3 conditions:

* 'suppress': Participants are instructed to not think about food/the story.
* 'button_press': Participants have double press the spacebar whenever they realize they think about food or the story.
* 'button_press_suppress': Both instructions from 'suppress' and 'button_press'.


## Setup

```sh
# clone
git clone git@github.com:GabrielKP/oc-pmc.git

# change to the dir of this project
cd conditions/psiturk-based/volition

# create conda environment
conda create -n psiturk python=3.8

# activate environment
conda activate psiturk

# install psyturk
pip install psiturk

# install python-Levenshtein (just to get rid of the warning...)
pip install python-Levenshtein

# Downgrade cryptography (to avoid error)
pip install cryptography==38.0.4

# turn on
psiturk server on

# turn off
psiturk server off
```

If there are version issues, try `pip install -r requirements.txt`.
This repo was created with:

```
python 3.9.15
psiturk 3.3.1
levenshtein 0.20.8
```

## Usage

Follow the setup instructions on your webserver.
Now you can use the scripts in `scripts` to control the server:
```sh
# turn server on
./scripts/server_on.sh
# the experiment will now be reachable at webserverurl:22362

# turn server off
./scripts/server_off.sh

# synchronize local changes to the server
./scripts/sync.sh [LV_HOST]
# whereas [LV_HOST] is the ip address (or ssh hostname) of your webserver
# this can also be set in your environment (export LV_HOST=[LV_HOST])

# download data
./scripts/get_data.sh [LV_HOST] [DATA_DIR]
# whereas [DATA_DIR] is the path to a copy of the `data` directory in this folder.
```

## Conditions

The condition can be set at server start-up via an environment variable
`export EXP_CONDITION="condition_name"`. "condition_name" can be one of the following:

* suppress, button_press, button_press_suppress: set the respective condition.
* button_press_both: will assign participants to 'button_press' and 'button_press_suppress' conditions equally. This option requires `num_conds = 2` in the [config.txt](config.txt).

## Experiment data data-structure

A data dir is denoted by starting with `data`. E.g. `data_experiment`.
The typical organization is:

```bash
data_experiment/
├── config
│   ├── eventdatafiles.txt
│   ├── story_condition_id.txt
│   ├── studyIDs.txt
│   └── trialdatafiles.txt
├── eventdata.csv
├── questiondata.csv
├── README.md
└── trialdata.csv
```

### Root data dir.

Root data dir, contains subdirs, raw
[`trialdata.csv`](https://psiturk.readthedocs.io/en/stable/recording.html#recording-trial-data),
`eventdata.csv`, `questiondata.csv` and a `README.md`.
Can contain multiple custom named csv files (e.g. `trialdata2.csv`).

### config

Contains config files for experiment:

- `eventdatafiles.txt`: all data files in the root dir containing eventdata (e.g. `eventdata.csv`). One file, one line.
- `trialdatafiles.txt`: all data files in the root dir containing trialdata (e.g. `trialdata.csv`, `trialdata2.csv`). One file, one line.
- `story_condition_id.txt`: The first line, contains the story name and the second line the condition name. For automatic import.
- `studyIDs.txt`: prolific studyIDs for which data is extracted in trialdatafiles.txt. One studyID, one line.
