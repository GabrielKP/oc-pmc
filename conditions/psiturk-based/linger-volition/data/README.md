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
- `story_condition_id.txt`: The first line, contains the story name and the second line the condition name. For automatic import with ldet.
- `studyIDs.txt`: prolific studyIDs for which data is extracted in trialdatafiles.txt. One studyID, one line.
