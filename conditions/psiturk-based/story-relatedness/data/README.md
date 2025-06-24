## Experiment data data-structure

A data dir is denoted by starting with `data`. E.g. `data_experiment`.
The typical organization is:

```bash
data_experiment/
├── config
│   ├── eventdatafiles.txt
│   ├── excluded_participantIDs_proposal.txt
│   ├── excluded_participantIDs.txt
│   ├── sql_exclusion.txt
│   ├── studyIDs.txt
│   └── trialdatafiles.txt
├── outputs
│   ├── moment_count.csv
│   ├── moment.csv
│   ├── moment_median.csv
│   ├── moment_raw.csv
│   ├── moment_variance.csv
│   ├── overview.txt
│   ├── README.md
│   ├── theme_count.csv
│   ├── theme.csv
│   ├── theme_median.csv
│   ├── theme_raw.csv
│   └── theme_variance.csv
├── plots
│   └── overview
│       ├── hist_count.png
│       ├── hist_rating_moment.png
│       ├── hist_rating_theme.png
│       ├── scatter_theme_moment.html
│       └── scatter_theme_moment.png
├── zipfiles
│   ├── plots.zip
│   └── ratings.zip
├── eventdata.csv
├── questiondata.csv
├── README.md
└── trialdata.csv
```

### Root data dir.

Root data dir, contains subdirs, raw
[`trialdata.csv`](https://psiturk.readthedocs.io/en/stable/recording.html#recording-trial-data),
`eventdata.csv`, `questiondata.csv` and this `README.md`.
Can contain multiple custom named csv files (e.g. `trialdata2.csv`).

### config

Contains config files for experiment:

- `eventdatafiles.txt`: all data files in the root dir containing eventdata (e.g. `eventdata.csv`). One file, one line.
- `trialdatafiles.txt`: all data files in the root dir containing trialdata (e.g. `trialdata.csv`, `trialdata2.csv`). One file, one line.
- `excluded_participantIDs.txt`: contains ids excluded from experiment. One ID, one line.
- `excluded_participantIDs_proposal.txt`: ids proposed to exclude. One ID, one line.
- `sql_exclusion.txt`: sql statement to exclude
- `studyIDs.txt`: prolific studyIDs for which data is extracted in trialdatafiles.txt
- `july`: file only present to mark it is a carver trial, for questionnaire answer analysis.

### outputs

Rating data extracted from raw datafiles.

Following files are contained (x = theme or x = moment):

- `x_raw.csv`: individual ratings
- `x.csv`: mean ratings
- `x_median.csv`: median ratings
- `x_count.csv`: word counts
- `x_variance.csv`: word variances
- `overview.txt`: file with some overview statistics
- `README.md`

Each file has a header in the first row (e.g. word,variance).

Moment words (event-related words may be a better fitting name) were rated
on this question:

- How related is the word to a specific moment within the story?
  (e.g. the word reminds you of specific details in the story)

Theme words were rated independently from each other based on this question:

- How related is the word to the general theme or mood of the story?
  (e.g. you feel the word is related, even though not to a specific moment)

### plots

Contains various basic histograms and plots.
To interactively plot all moment vs theme ratings open
`scatter_themme_moment.html` in your browser

### zipfiles

Contains `plots.zip` and `ratings.zip`, which are a compressed version of the
other folders in the experiment directory.
Generated with `scripts/process.sh data_experiment`.
