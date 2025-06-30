"""This script helps with correcting words participants generated.
The script is also useful after changes to corrected.csv/discarded.csv
to update processed.csv and corrected_words_to_rate.txt.
Just press 5 for the first word (if you have to).

Input:
- words_to_rate
- OR "additional_words.txt" generated with
    export/words_additional.py

Output:
- updated processed.csv / discarded.csv / corrections.csv (see below)
- updated corrected_words_to_rate.txt

Additional files this script operates on.
corrections/processed.csv
    Tracks all words that have been checked, corrected or discarded.
corrections/discarded.csv
    Tracks all the words for which not a useful rating is possible due to
    ambiguity or lack of signal.
corrections/corrections.csv
    Tracks all misspelled words and their corrections.
"""

import os
from typing import Any, Dict

from oc_pmc import CORRECTIONS_DIR, DATA_DIR, WORDS_DIR, get_logger
from oc_pmc.load import load_dict, load_word_list_txt, load_words
from oc_pmc.utils import check_make_dirs
from spellchecker import SpellChecker

log = get_logger(__name__)


def export_story_words(config: Dict[str, Any]):
    # load words to rate
    if config["from_additional_words"]:
        path_additional_words = os.path.join(
            DATA_DIR, WORDS_DIR, config["story"], "additional_words.txt"
        )
        words_to_correct = set(load_word_list_txt(path_additional_words))
    else:
        words_to_correct = set(load_words(config))

    path_corrected_words_to_rate = os.path.join(
        DATA_DIR, WORDS_DIR, config["story"], "corrected_words_to_rate.txt"
    )
    check_make_dirs(path_corrected_words_to_rate)

    # load words to rate that are processed
    path_processed_words = os.path.join(DATA_DIR, CORRECTIONS_DIR, "processed.csv")
    if not os.path.isfile(path_processed_words):
        check_make_dirs(path_processed_words)
        processed_words = set()
    else:
        processed_words = set(load_word_list_txt(path_processed_words))

    # load word corrections
    path_corrections = os.path.join(DATA_DIR, CORRECTIONS_DIR, "corrections.csv")
    if not os.path.isfile(path_corrections):
        log.info(f"Mapping for corrected words not found: {path_corrections}")
        check_make_dirs(path_corrections)
        correct_mapping = dict()
        incorrect_words_taken_care_of = set()
    else:
        log.info(f"Mapping for corrected words found: {path_corrections}")
        correct_mapping = load_dict(path_corrections)
        incorrect_words_taken_care_of = set(correct_mapping.keys())

    # load discarded words
    path_discarded = os.path.join(DATA_DIR, CORRECTIONS_DIR, "discarded.csv")
    if os.path.isfile(path_discarded):
        log.info(f"Found discarded words: {path_discarded}")
        words_discarded = set(load_word_list_txt(path_discarded))
    else:
        log.info(f"Discarded words not found: {path_discarded}")
        words_discarded = set()

    # subtract words already processed
    words_to_correct.difference_update(processed_words)
    # (these should be subtracted already, but to make sure.)
    # subtract incorrect words taken care of
    words_to_correct.difference_update(incorrect_words_taken_care_of)
    # subtract discarded words
    words_to_correct.difference_update(words_discarded)

    # spell check words
    spellcheck = SpellChecker()
    misspelled = spellcheck.unknown(words_to_correct)

    log.info(f"Misspelled words: {len(misspelled)}")
    log.info("Correcting words:")
    helptext = (
        "1: previous; 2: keep; 3: suggestion; 4: discard; 5: exit;"
        " Type the word to correct"
    )
    word = ""
    previous_word = ""
    option = -1
    previous_option = -1
    suggestion = ""
    previous_suggestion = ""
    correction = ""
    previous_correction = ""
    # track word corrections and save separately
    while len(misspelled) > 0:
        print(helptext)

        # if resetting, do not resample, but save previous word
        if option == 1:
            misspelled.add(word)
            word = previous_word
        else:
            word = misspelled.pop()

        suggestion = spellcheck.correction(word)
        suggestion = "" if suggestion is None else suggestion
        u_in = input(f"{word} | suggestion: {suggestion} | ")
        try:
            option = int(u_in)
            correction = ""
        except ValueError:
            option = 6
            correction = u_in

        if option == 1:
            # jump back
            continue

        # process previous word
        if previous_option == 2:
            # keep
            processed_words.add(previous_word)
        if previous_option == 3:
            # correction: suggestion
            processed_words.add(previous_suggestion)
            correct_mapping[previous_word] = previous_suggestion
        if previous_option == 4:
            # discard
            words_discarded.add(previous_word)
        if previous_option == 6:
            # correction: manual
            processed_words.add(previous_correction)
            correct_mapping[previous_word] = previous_correction

        # exit if wanted
        if option == 5:
            break

        previous_word = word
        previous_option = option
        previous_suggestion = suggestion
        previous_correction = correction

    log.info(f"Misspelled words left: {len(misspelled)}")
    log.info(f"Saving processed words to {path_processed_words}")
    # add newly processed words
    processed_words.update(words_discarded, correct_mapping.keys())

    # write processed words
    with open(path_processed_words, "w") as f_out:
        f_out.writelines("\n".join(processed_words) + "\n")

    # write corrected words
    log.info(f"Saving corrected word mapping to {path_corrections}")
    with open(path_corrections, "w") as f_out:
        lines = [f"{key},{value}" for key, value in correct_mapping.items()]
        f_out.writelines("key,value\n" + "\n".join(lines) + "\n")

    # write discarded words
    log.info(f"Saving discarded words to {path_discarded}")
    with open(path_discarded, "w") as f_out:
        f_out.writelines("\n".join(words_discarded) + "\n")

    # write the corrected words to rate
    log.info(f"Saving corrected words to rate {path_corrected_words_to_rate}")
    corrected_words_to_rate = set()
    for word in words_to_correct:
        if word in correct_mapping:
            corrected_words_to_rate.add(correct_mapping[word])
        elif word in words_discarded:
            continue
        else:
            corrected_words_to_rate.add(word)
    with open(path_corrected_words_to_rate, "w") as f_out:
        f_out.writelines("\n".join(corrected_words_to_rate) + "\n")


if __name__ == "__main__":
    config = {
        "story": "carver_original",
        "from_additional_words": True,
        "corrections": True,
    }
    export_story_words(config)
