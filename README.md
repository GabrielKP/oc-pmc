
<h1 align="center">Origin and Control of Persistent Mental Content</h1>

<p align="center">Code & data accompanying the paper by Kressin Palacios, G, Bellana, B, and Honey, CJ</p>

<p align="center">
<a href="https://www.python.org/"><img alt="code" src="https://img.shields.io/badge/code-Python%203.9-blue?logo=Python"></a>
<a href="https://docs.astral.sh/ruff/"><img alt="Code style: Ruff" src="https://img.shields.io/badge/code%20style-Ruff-green?logo=Ruff"></a>
<a href="https://python-poetry.org/"><img alt="packaging framwork: Poetry" src="https://img.shields.io/badge/packaging-Poetry-lightblue?logo=Poetry"></a>
<a href="https://osf.io/preprints/psyarxiv/dghnf"><img alt="preprint server: PsyArXiv" src="https://img.shields.io/badge/preprint-PsyArXiv/dghnf-red?color=%23cf1e36"></a>
</p>

---

This repository contains:
* [the code to generate the figures and analyses of the manuscript;](README.md#analyses--figures)
* [the experimental code used to collect the data;](README.md#conditions)
* [the anonymized data.](README.md#data)

> [!NOTE]
> Please do not hesitate to [open an issue](https://github.com/GabrielKP/oc-pmc/issues/new) if you encounter problems during setup or write an [email](mailto:gkressi1@jhu.edu) with questions!


## Experimental conditions

The experimental conditions have different names in the repository and the manuscript:

| Name in paper            | Repository:story    | Repository:condition                         | from [Bellana et al. 2022](https://www.nature.com/articles/s41467-022-32113-6) |
| ------------------------ | ------------------- | -------------------------------------------- | :----------------------------------------------------------------------------: |
| Intact                   | carver_original     | button_press                                 |                                       no                                       |
| Scrambled                | carver_original     | word_scrambled                               |                                      yes                                       |
| Suppress                 | carver_original     | button_press_suppress                        |                                       no                                       |
| Baseline                 | carver_original     | neutralcue2                                  |                                       no                                       |
| Suppress No Button Press | carver_original     | suppress                                     |                                       no                                       |
| Situation                | carver_original     | interference_situation                       |                                       no                                       |
| Tom                      | carver_original     | interference_tom                             |                                       no                                       |
| New Story                | carver_original     | interference_story_spr                       |                                       no                                       |
| Geometry                 | carver_original     | interference_geometry                        |                                       no                                       |
| Continued                | carver_original     | interference_story_spr_end_continued         |                                       no                                       |
| Separated                | carver_original     | interference_story_spr_end_separated         |                                       no                                       |
| Delayed Continued        | carver_original     | interference_story_spr_end_delayed_continued |                                       no                                       |
| Pause                    | carver_original     | interference_pause                           |                                       no                                       |
| End Cue + Pause          | carver_original     | interference_end_pause                       |                                       no                                       |
| New Story Alone          | dark_bedroom        | neutralcue                                   |                                       no                                       |
| -                        | carver_original     | neutralcue                                   |                                      yes                                       |



## Analyses & figures

_To run the code, you require a computer capable of running python 3.9._
```sh
git clone git@github.com:GabrielKP/oc-pmc.git
cd oc-pmc

# (optional, but good practice)
conda create -n oc-pmc python=3.9 -y
conda activate oc-pmc

# to reproduce
pip install .

# REPRODUCTION: this script will run all analyses and create all plots from the paper.
python analysis/main.py
```
_Installation time usually does not take longer than 5 minutes, but can vary based on your internet connection._
_You should see analyses outputs in the terminal, and plots in the `plots` folder. The complete reproduction usually runs within 15 minutes._

### Other scripts

To compute the theme similarity for words to the theme words of a story, you need to setup glove:
1. Download glove embeddings [https://nlp.stanford.edu/projects/glove/](https://nlp.stanford.edu/projects/glove/) -  version: Wikipedia 2014 + Gigaword 5 (glove.6B.zip).
2. Extract and place the file `glove.6B.300d.txt` into the directory [/Volumes/opt/oc-pmc/data/external/glove](/Volumes/opt/oc-pmc/data/external/glove).

```sh
# Compute theme similarity
python analysis/rate_themesim.py
# to compute the theme similarity, you need to download and extract 

# Run exclusion scripts
python analysis/oc_pmc/exclusions/[condition].py

# Import raw data:
# - you need raw data (not published)
# - set the paths to the data folders in the .env
python analysis/oc_pmc/do_import/manuscript.py
```

### For development

Instead of `pip install .`, install and use [poetry](https://python-poetry.org/docs/#installation) for dependency management:
```sh
# use poetry instead of pip install .
poetry install

```


### Parameters for the `.env`

Placing an `.env` in the root directory allows you to change paths to some dependencies:
```sh
DATA_DIR=/path/to/data_dir
# ...
```

* `DATA_DIR`: Folder containing all data (default: `data`)
* `OUTPUTS_DIR`: Folder were computing/rating outputs will be saved to, it makes sense that this is the same as `DATA_DIR` (default: `data`)
* `STUDYPLOTS_DIR`: Folder where all plots will be saved to (default: `plots`)
* `STUDYDATA_DIR`: Data folder of psyserver-based studies
* `BELLANA_DIR`: Data repository from Bellana et al. 2022 [https://osf.io/dmbx4/](https://osf.io/dmbx4/)



## Data Collection Platforms for Each Condition

Studies were collected in two different frameworks: psiTurk, and PsyServer.


### Psiturk-based: story relatedness ratings, suppress, button_press, button_press_suppress

The studies were hosted on AWS with [psiTurk](https://github.com/NYUCCL/psiTurk.git).

* Story relatedness ratings: [readme](conditions/psiturk-based/story-relatedness/README.md)
* Linger volition (suppress/button_press/button_press_suppress): [readme](conditions/psiturk-based/linger-volition/README.md)


### Psyserver-based: all other conditions

The studies were hosted on AWS with [https://github.com/GabrielKP/psyserver](PsyServer).
All studies are structured similarily: we used [bootstrap](https://getbootstrap.com/), [jquery](https://jquery.com/), and [requirejs](https://requirejs.org/).
The html code is in the root directory or component-organized directories that are in the root directory. The javascript code is in a directory `static/js` which contains following files and directories:
* **main.js**: Main javascript file, specifying configuration and order of study.
* **component**: Modules with a logic that can be reused, or structured data. E.g. the code to display a single page (`Pages.js`), the free association code (`FreeAssociation.js`) or the story (`Carver.js`).
* **module**: Background modules that organize data storing and saving (`Data.js`) or the study initializing and study progression (`Study.js`).
* **stage**: Experimental stages. Each module corresponds to a logical stage and may use components. For example (`GeneralInstructions.js`) or (`Reading.js`).

To start any of the conditions, you can open the `starter.html` in your browser and then start the study.
To run the studies properly, the data saving is setup to interact with PsyServer.
You can simply upload the entire studies directory into the `studies` psyserver folder or use the scripts in the live [studies](https://github.com/gabrielKP/studies/) repository.

#### Conditions:

* dark_bedroom/neutralcue: [conditions/psyserver-based/linger-fa-dark-bedroom](conditions/psyserver-based/linger-fa-dark-bedroom)
* interference_end_pause: [conditions/psyserver-based/linger-interference-end-pause](conditions/psyserver-based/linger-interference-end-pause)
* interference_geometry: [conditions/psyserver-based/linger-interference-geometry](conditions/psyserver-based/linger-interference-geometry)
* interference_pause: [conditions/psyserver-based/linger-interference-pause](conditions/psyserver-based/linger-interference-pause)
* interference_situation: [conditions/psyserver-based/linger-interference-situation](conditions/psyserver-based/linger-interference-situation)
* interference_story_spr: [conditions/psyserver-based/linger-interference-story-spr](conditions/psyserver-based/linger-interference-story-spr)
* interference_story_spr_end_continued/interference_story_spr_end_separated/interference_story_spr_end_delayed_continued: [conditions/psyserver-based/linger-interference-story-spr-end](conditions/psyserver-based/linger-interference-story-spr-end)
* interference_tom: [conditions/psyserver-based/linger-interference-tom](conditions/psyserver-based/linger-interference-tom)
* neutralcue2: [conditions/psyserver-based/linger-neutralcue2/](conditions/psyserver-based/linger-neutralcue2)



## Data

The `data` directory contains the experimental data.

Each subdirectory is usually arranged by `story/condition/file` indicating the respective condition the data comes from.

The following subdirectories are included:

* **corrections**: Contains three files:
    * *processed.csv*: Tracks all words that have been checked, corrected or discarded.
    * *discarded.csv*: Tracks all the words for which not a useful rating is possible due to ambiguity or lack of intellegibility.
    * *corrections.csv*: Tracks all misspelled words and their corrections.
* **double_press**: The food- (pre-reading) and story- (post-reading) thoughts participants reported in the button_press & button_press_suppress conditions. Every row represents a button-press. Note that participants may did not report any double-press at all, in which case they will not have a single row in the file.
    * *participantID*: anonymized identifier for a participant, **it is only unique within a condition, but not across conditions!**
    * *timestamp*: time double-press was registered since start of free association in ms.
    * *current_double_press_count*: the count of double pressess, starting at 1.
    * *time_since_last_word_start*: time double-press was registered since submission of the last word in ms.
    * *word_count*: the count of words which were submitted before double-press since start of free association, the count starts at 0.
    * *word_text*: the text currently typed in the textbox at the time of the double-press.
    * *word_key_onsets*: the relative time of keys pressed since last submission of a word at the time of the double-press.
    * *word_key_chars*: the characters of keys pressed since last submission of a word at the time of the double-press.
    * *word_key_codes*: the javascript keycode for each pressed key (https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/keyCode) since the last submission of a word at the time of the double-press
    * *word_double_press_count*: the number of double-presses that happened since the last submission of a word.
* **external**: Empty directory to unzip glove embeddings to if used for rating.
* **manual**: Categorizations of free-form responses by paid undergraduate research assistants. The rating keys can be found in the [readme](data/manual/fields/README.md).
* **questionnaires**: Most of the questionnaire and experimental data. Each directory contains at least the following files:
    * `summary.csv` (and sometimes separate in `questionnaire_data.csv`) - the most important fields:
        * *participantID*: anonymized identifier for a participant, **it is only unique within a condition, but not across conditions!**
        * *comp_prop*: comprehension score (see paper).
        * *tran_prop*: transportation score (see paper).
        * *linger_rating*: Self-reported lingering (see paper).
        * *wcg_strategy*: Free form answer about which strategy participants used (see Supplementary Information).
        * *volition*: Answer to volition question (see Supplementary Information).
        * The file also contains the unix-timestamps for phase starts/ends, and the answers to all questions participants answered, these mostly match with the question id in the html/javascript condition code.
    * `exclusions.csv`.
        * *participantID*: anonymized identifier for a participant, **it is only unique within a condition, but not across conditions!**
        * *exclusion*: Whether a participant was included or excluded.
* **rated_words**: Story-relatedness ratings. The data is arranged by `approach/model/story/file`. Approach refers to broad approach (human or theme_similarity), model as the subcategory (e.g. moment or theme ratings), and story refers to the story to which the relatedness of the words was rated to.
* **stories**: Plain-text files for the stories used in our conditions. The `provost_original` story was used as a familiarization story at the beginning of the interference_story_spr condition.
* **theme_words**: The theme words for each story used to compute theme similarity. A .txt file ordered by the frequency participants generated keywords in the keyword phase of the study. The data for carver_original comes from Bellana et al. 2022.
* **time_words**: Participant generated words during free association. Each row represents a word a participant generated. It contains following columns:
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
* **words_to_rate**: the word files used to rate the words for story relatedness (for documentation purposes), updated versions can be created with [analysis/oc_pmc/export/words.py](analysis/oc_pmc/export/words.py)



*Good luck on your adventures.*
