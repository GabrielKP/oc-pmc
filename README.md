
<h1 align="center">Origin and Control of Persistent Mental Content</h1>

<p align="center">Code & data accompanying the paper by Kressin Palacios, G, Bellana, B, and Honey, C. J.</p>

<p align="center">
<a href="https://www.python.org/"><img alt="code" src="https://img.shields.io/badge/code-Python-blue?logo=Python"></a>
<a href="https://docs.astral.sh/ruff/"><img alt="Code style: Ruff" src="https://img.shields.io/badge/code%20style-Ruff-green?logo=Ruff"></a>
<a href="https://python-poetry.org/"><img alt="packaging framwork: Poetry" src="https://img.shields.io/badge/packaging-Poetry-lightblue?logo=Poetry"></a>
</p>

---

This repository contains the code to generate the figures and analyses of the paper, the code to collect the experimental conditions, and the anonymized data.

The repository uses different names for the conditions than the paper:

| Paper-name               | Repository:story | Repository:condition                         | from Bellana et al. 2022 |
| ------------------------ | ---------------- | -------------------------------------------- | :----------------------: |
| Intact                   | carver_original  | button_press                                 |            no            |
| Scrambled                | carver_original  | word_scrambled                               |           yes            |
| Suppress                 | carver_original  | button_press_suppress                        |            no            |
| Baseline                 | carver_original  | neutralcue2                                  |            no            |
| Suppress-no-button-press | carver_original  | suppress                                     |            no            |
| Situation                | carver_original  | interference_situation                       |            no            |
| Tom                      | carver_original  | interference_tom                             |            no            |
| New story                | carver_original  | interference_story_spr                       |            no            |
| Geometry                 | carver_original  | interference_geometry                        |            no            |
| Continued                | carver_original  | interference_story_spr_end_continued         |            no            |
| Separated                | carver_original  | interference_spr_end_separated               |            no            |
| Delayed-continued        | carver_original  | interference_story_spr_end_delayed_continued |            no            |
| Pause                    | carver_original  | interference_pause                           |            no            |
| End-cue + Pause          | carver_original  | interference_end_pause                       |            no            |
| New story alone          | dark_bedroom     | neutralcue                                   |            no            |
| -                        | carver_original  | neutralcue*                                  |           yes            |

*We include this condition here as we used data from it for outlier computation in the exclusion criteria of our early studies.

## Analyses & figures

```sh
git clone git@github.com:GabrielKP/oc-pmc.git
cd oc-pmc
```





## Conditions


### Psiturk-based: (suppress, button_press, button_press_suppress)

The studies were hosted on AWS with [https://github.com/NYUCCL/psiTurk.git](psiTurk).

* Story relatedness ratings: [readme](conditions/psiturk-based/story-relatedness/README.md)
* Linger volition (internal names in parenthesis): Intact (button_press), Suppress (button_press_suppress), suppress (Suppress-no-button-press)


### Psyserver-based: All other conditions

The studies were hosted on AWS with [git@github.com:GabrielKP/psyserver.git](PsyServer).

Studies collected with psiturk (legacy code):

- carver_original/linger_volition (suppress, button_press, button_press_suppress)
- carver_original/linger_ocd

## Data

The `data` folder contains all the data used for the analyses and figures.
Each subfolder is usually arranged by story/condition/filename, whereas the filename indicates something about the data as well, for example it may be post/pre/practice to indicate which phase the data came from.

Following subfolders are included:

* **stories**: Plain-text files for the stories used in our conditions. The `provost_original` story was used as a familiarization story at the beginning of the interference_story_spr condition.
* **time_words**: Participant generated words during free association. It contains following fields
    * *participantID*: anonymized identifier for a participant, **it is only unique within a condition, but not across conditions!**
    * *word_text*: the word a participant typed
    * *word_count*: the number of the word, starting at 0
    * *word_time*: submission time (when participants pressed enter) of word in ms, relative to previous word
    * *word_key_onsets*: the time of each pressed key, relative to previous key-press
    * *word_key_chars*: the character of each pressed key
    * *word_key_codes*: the javascript keycode for each pressed key (https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/keyCode)
    * *timestamp*: the timestamp at word submission in ms since free association start,
    * *timestamp_absolute*: the UNIX time stamp at word submission
    * *word_double_press_count* (only button press studies): total number of double-presses after previous word and before submission of the word.
    * *story_relatedness* (only some studies): mean 'moment' story relatedness - I recommend not using this value at it may be outdated, and just rerating each word.

* **time_words_legacy**: public word chain data from Bellana et al. 2022, needed when using the raw data import.
* **words_to_rate**: the word files used to rate the words for story relatedness (for documentation purposes), updated versions can be created with [analysis/ldet/export/words.py](analysis/ldet/export/words.py)

## Raw data

The raw data is not shared, however for completeness, here is how you would import it.

### Psiturk-based studies



### Psyserver-based studies

### Bellana et al. (2022) data

1. Download raw data from: [https://osf.io/dmbx4/](https://osf.io/dmbx4/)
2. Unzip and place appropriately
3. In `.env` set `BELLANA_DIR="</path/to/unzipped/folder>"`


## Original repositories

This repository is the merger of many private and public repositories used for the project:

* Story relatedness ratings: https://github.com/GabrielKP/story-relatedness
* Volition studies



*Good luck on your adventures.*
