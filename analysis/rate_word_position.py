import argparse
import math
import pickle
import re
import shutil
import signal
from itertools import product
from pathlib import Path
from typing import List, Optional, Union, cast

import numpy as np
import pandas as pd
from dotenv import dotenv_values
from oc_pmc import DATA_DIR, OUTPUTS_DIR, get_logger
from oc_pmc.load import load_story_sentences, load_story_sentences_grouped, load_words
from oc_pmc.model_objects.model_glove import Glove
from oc_pmc.utils import check_make_dirs, get_n_sections, print_config
from openai import OpenAI
from openai.types.responses import Response
from sentence_transformers import CrossEncoder, SentenceTransformer
from tqdm import tqdm

WORD_POSITION_DIR = "word_position"


log = get_logger(__name__)

PRICES_DOLLAR_PER_MILLION_TOKENS = {
    "gpt-5-mini": {
        "input": 1.25,
        "output": 2.00,
    },
}


def cosine_similarity(tensor_a: np.ndarray, tensor_b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between each row of tensor_a and each row of tensor_b.

    Parameters
    ----------
    tensor_a : np.ndarray
        Tensor of shape (A, D).
        D is the vector space dimension (embedding dimension).
    tensor_b : np.ndarray
        Tensor of shape (B, D).

    Returns
    -------
    np.ndarray
        Tensor of shape (A, B).
    """
    assert tensor_a.shape[1] == tensor_b.shape[1], "Dimension on axis 1 must match"
    # cosine similarity (a, b) = (a * b) / (|a| * |b|)
    dot_a_b = np.einsum("ad, bd -> ab", tensor_a, tensor_b)
    norm_a = np.linalg.norm(tensor_a, axis=1)
    norm_b = np.linalg.norm(tensor_b, axis=1)
    norm_a_b = np.einsum("a, b -> ab", norm_a, norm_b)
    return dot_a_b / norm_a_b


def correlation(tensor_a: np.ndarray, tensor_b: np.ndarray) -> np.ndarray:
    """Compute correlation between each row of tensor_a and each row of tensor_b.

    Parameters
    ----------
    tensor_a : np.ndarray
        Tensor of shape (A, D).
        D is the vector space dimension (embedding dimension).
    tensor_b : np.ndarray
        Tensor of shape (B, D).

    Returns
    -------
    np.ndarray
        Tensor of shape (A, B).
    """
    assert tensor_a.shape[1] == tensor_b.shape[1], "Dimension on axis 1 must match"
    # correlation (a, b) = cov(a, b) / (std(a) * std(b))
    # cov(a, b) = E[(a - E[a])(b - E[b])]
    centered_a = tensor_a - np.mean(tensor_a, axis=1, keepdims=True)
    centered_b = tensor_b - np.mean(tensor_b, axis=1, keepdims=True)
    cov_a_b = np.einsum("ad, bd -> ab", centered_a, centered_b) / (tensor_a.shape[1])
    # std(a) * std(b)
    std_a = np.std(tensor_a, axis=1)
    std_b = np.std(tensor_b, axis=1)
    std_a_b = np.einsum("a, b -> ab", std_a, std_b)
    return cov_a_b / std_a_b


def rate_word_position_embeddings_example(
    model_name: Optional[str] = None,
    section_aggregation: Optional[str] = None,
):
    if section_aggregation is None:
        section_aggregation = "top3"
        log.info(
            f"No section aggregation provided, using default {section_aggregation=}"
        )

    story = "word_position_test_story"

    config = {
        "mode": "embeddings",
        "model_name": model_name,
        "section_aggregation": section_aggregation,
        "story": story,
    }
    print_config(config)

    # load story
    sentences = load_story_sentences(story, story_file="sectioned.txt")
    # load all words
    # words = list(set([word.strip() for word in load_words(corrections=True)]))
    words = ["fish", "murder", "camping", "river", "beer", "jacket", "pillow"]
    # load model
    if model_name is None:
        model_name = "google/embeddinggemma-300m"
        log.info(f"No model name provided, using default model: {model_name}")
    model = SentenceTransformer(model_name)

    # (A) Compute word-sentence similarities without section grouping

    # embed words
    word_embeddings = model.encode(words)

    # embed sentences
    sentence_embeddings = model.encode(sentences)

    # similarity
    word_sentence_similarities = correlation(word_embeddings, sentence_embeddings)
    # shape = (n_words, n_sentences)
    word_sentence_scores_df = pd.DataFrame(
        np.round(word_sentence_similarities, 2),
        index=words,  # type: ignore
        columns=range(
            len(sentences),
        ),
    )

    # (B) Compute word-sentence similarities with section grouping
    section_sentences = load_story_sentences_grouped(story, story_file="sectioned.txt")

    embedded_sections_list: List[np.ndarray] = list()
    for section_sentences_ in section_sentences:
        embedded_section = model.encode(section_sentences_)
        # shape = (n_sentences, embed_dim)
        embedded_sections_list.append(embedded_section)

    # compute score for each section
    word_section_scores = np.empty((len(words), len(embedded_sections_list)))
    for idx_section, section_embedding in enumerate(embedded_sections_list):
        section_word_similarities = correlation(word_embeddings, section_embedding)
        # shape = (n_words, n_sentences)
        if section_aggregation == "mean":
            word_scores = np.mean(section_word_similarities, axis=1)
        elif section_aggregation == "max":
            word_scores = np.max(section_word_similarities, axis=1)
        elif section_aggregation == "top3":
            word_scores = np.mean(
                np.sort(section_word_similarities, axis=1)[:, -3:], axis=1
            )
        else:
            raise ValueError(f"Invalid section aggregation: {section_aggregation}")
        word_section_scores[:, idx_section] = word_scores

    # output section scores
    word_section_scores_df = pd.DataFrame(
        np.round(word_section_scores, 2),
        index=words,  # type: ignore
        columns=range(
            len(embedded_sections_list),
        ),
    )

    # Save scores to file for demonstration purposes.
    print("For test story and test words:")
    output_path = Path(OUTPUTS_DIR, WORD_POSITION_DIR, story, "embeddings", model_name)
    check_make_dirs(str(output_path), isdir=True, verbose=False)

    # word-sentence scores
    path_word_sentence_scores = output_path / "word_sentence_scores.csv"
    print(f" - Saving word-sentence scores to file: {path_word_sentence_scores}")
    word_sentence_scores_df.to_csv(path_word_sentence_scores, sep="\t", index=True)

    # word-section scores
    path_word_section_scores = output_path / "word_section_scores.csv"
    print(f" - Saving word-section scores to file: {path_word_section_scores}")
    word_section_scores_df.to_csv(path_word_section_scores, sep="\t", index=True)


def rate_word_position_reranker(
    story: str,
    model_name: Optional[str] = None,
    section_aggregation: Optional[str] = None,
):
    if section_aggregation is None:
        section_aggregation = "top3"
        log.info(
            f"No section aggregation provided, using default {section_aggregation=}"
        )

    story = "word_position_test_story"

    config = {
        "mode": "reranker",
        "model_name": model_name,
        "section_aggregation": section_aggregation,
        "story": story,
    }
    print_config(config)

    # load story
    sentences = load_story_sentences(story, story_file="sectioned.txt")
    # load all words
    # words = list(set([word.strip() for word in load_words(corrections=True)]))
    words = [
        "fish",
        "murder",
        "camping",
        "river",
        "beer",
        "jacket",
        "pillow",
        "funeral",
        "corpse",
    ]
    # load model
    if model_name is None:
        log.info(f"No model name provided, using default model: {model_name}")
        model_name = "BAAI/bge-reranker-v2-m3"
    model = CrossEncoder(model_name)

    # (A) Compute word-sentence scores without section grouping
    word_sentence_scores = np.empty((len(words), len(sentences)))
    for idx_word, word in enumerate(tqdm(words, desc="Computing word-sentence scores")):
        word_sentence_pairs = list(product([word], sentences))
        scores = model.predict(word_sentence_pairs)
        word_sentence_scores[idx_word] = scores

    # shape = (n_words, n_sentences)
    word_sentence_scores_df = pd.DataFrame(
        np.round(word_sentence_scores, 2),
        index=words,  # type: ignore
        columns=range(
            len(sentences),
        ),
    )

    # (B) Compute word-sentence scores with section grouping
    section_sentences = load_story_sentences_grouped(story, story_file="sectioned.txt")

    word_section_scores = np.empty((len(words), len(section_sentences)))
    for idx_section, section_sentences_ in enumerate(
        tqdm(section_sentences, desc="Computing word-section scores")
    ):
        # compute score for each section
        word_sentence_scores_section = np.empty((len(words), len(section_sentences_)))
        # shape = (n_words, n_sentences_section)
        for idx_word, word in enumerate(words):
            word_sentence_pairs = list(product([word], section_sentences_))
            scores = model.predict(word_sentence_pairs)
            word_sentence_scores_section[idx_word] = scores

        # aggregate
        if section_aggregation == "mean":
            word_scores_section = np.mean(word_sentence_scores_section, axis=1)
        elif section_aggregation == "max":
            word_scores_section = np.max(word_sentence_scores_section, axis=1)
        elif section_aggregation.startswith("top"):
            top_n = int(section_aggregation[3:])
            word_scores_section = np.mean(
                np.sort(word_sentence_scores_section, axis=1)[:, -top_n:], axis=1
            )
        else:
            raise ValueError(f"Invalid section aggregation: {section_aggregation}")
        word_section_scores[:, idx_section] = word_scores_section

    # output section scores
    word_section_scores_df = pd.DataFrame(
        np.round(word_section_scores, 2),
        index=words,  # type: ignore
        columns=range(
            len(section_sentences),
        ),
    )
    print(word_sentence_scores_df)
    print(word_section_scores_df)
    return word_section_scores_df


def load_section_theme_words(story: str) -> List[List[str]]:
    path = Path(DATA_DIR, "theme_words", story, "section_theme_words.txt")
    with open(path, "r") as f_in:
        section_strings = f_in.read().split("***\n")
    section_theme_words = [
        section_string.strip().split("\n")
        for section_string in section_strings
        if section_string.strip() != ""
    ]
    return section_theme_words


def rate_word_position_themesim(
    story: str,
    section_aggregation: Optional[str] = None,
):
    # for config & saving
    mode = "themesim"
    model_class = Glove
    model_name = "glove"
    if section_aggregation is None:
        section_aggregation = "top3"
        log.info(
            f"No section aggregation provided, using default{section_aggregation=}"
        )

    config = {
        "mode": mode,
        "model_name": model_name,
        "section_aggregation": section_aggregation,
        "story": story,
    }
    print_config(config)

    # load section theme words
    section_theme_words = load_section_theme_words(story)

    # load all words
    words = list(set([word.strip() for word in load_words(corrections=True)]))

    # load model
    model = model_class(config=dict())

    # compute theme word embeddings
    section_theme_word_embeddings_list = list()
    for section_theme_words_ in section_theme_words:
        section_theme_word_embeddings_list.append(
            np.stack(
                cast(
                    List[np.ndarray],
                    model.embeddings(config=dict(), words=section_theme_words_),
                ),
                axis=0,
            )
        )
    # could stack them but then cannot reuse code from other functions

    # embed words
    word_embeddings_list_with_nan = model.embeddings(config=dict(), words=words)
    word_mask = [emb is not None for emb in word_embeddings_list_with_nan]
    word_embeddings_list = cast(
        List[np.ndarray],
        [emb for emb in word_embeddings_list_with_nan if emb is not None],
    )
    word_embeddings = np.stack(word_embeddings_list, axis=0)

    word_section_scores = np.empty(
        (len(word_embeddings_list), len(section_theme_word_embeddings_list))
    )
    for idx_section, section_embeddings in enumerate(
        section_theme_word_embeddings_list
    ):
        section_word_similarities = correlation(word_embeddings, section_embeddings)
        # shape = (n_words, n_sentences)
        if section_aggregation == "mean":
            word_scores = np.mean(section_word_similarities, axis=1)
        elif section_aggregation == "max":
            word_scores = np.max(section_word_similarities, axis=1)
        elif section_aggregation.startswith("top"):
            top_n = int(section_aggregation[3:])
            word_scores = np.mean(
                np.sort(section_word_similarities, axis=1)[:, -top_n:], axis=1
            )
        else:
            raise ValueError(f"Invalid section aggregation: {section_aggregation}")
        word_section_scores[:, idx_section] = word_scores

    word_section_scores_df = pd.DataFrame(
        np.round(word_section_scores, 2),
        index=np.array(words)[word_mask],  # type: ignore
        columns=range(
            len(section_theme_word_embeddings_list),
        ),
    )

    output_path = Path(
        OUTPUTS_DIR,
        WORD_POSITION_DIR,
        story,
        mode,
        model_name,
        f"{section_aggregation}.csv",
    )
    check_make_dirs(output_path, verbose=False)
    word_section_scores_df.to_csv(output_path, index=True)
    print(f"Saved word-section scores to {output_path}")


def parse_incontext_response(
    response: Response,
    word_regex: re.Pattern,
    section_id_regex: re.Pattern,
    section_score_regex: re.Pattern,
    alt_section_score_regex: re.Pattern,
    n_sections: int,
    rated_words_and_sections_dct: dict[str, list],
) -> tuple[dict[str, list], list[str]]:
    failed_lines: list[str] = list()
    for line in response.output_text.split("\n"):
        if line.strip() == "":
            continue
        word = word_regex.search(line)
        section_id = section_id_regex.search(line)
        section_score = section_score_regex.search(line)
        if word is None or section_id is None:
            failed_lines.append("Parsing error: " + line)
            continue
        if section_score is None:
            section_score = alt_section_score_regex.search(line)
            if section_score is None:
                failed_lines.append("Parsing error: " + line)
                continue
        try:
            word_str = str(word.group(1))
            section_id_int = int(section_id.group(1))
            section_score_int = int(section_score.group(1))
            if (
                section_id_int < 1
                or section_id_int > n_sections
                or section_score_int < 0
                or section_score_int > 4
            ):
                failed_lines.append("Out of bounds: " + line)
                continue
        except Exception:
            failed_lines.append("Invalid type: " + line)
            continue

        if word_str not in rated_words_and_sections_dct:
            rated_words_and_sections_dct[word_str] = [-1] * n_sections

        if rated_words_and_sections_dct[word_str][section_id_int - 1] != -1:
            log.warning(f"Duplicate rating: {word_str} - section {section_id_int}")
            failed_lines.append("duplicate: " + line)
            continue

        rated_words_and_sections_dct[word_str][section_id_int - 1] = section_score_int
    return rated_words_and_sections_dct, failed_lines


def word_position_incontext_reprocess(
    story: str,
    model_name: Optional[str] = None,
    batch_size: Optional[int] = None,
):
    log.warning("REPROCESSING RAW RESPONSES")

    # register keyboard interrupt in all cases
    signal.signal(signal.SIGINT, signal.default_int_handler)

    if model_name is None:
        model_name = "gpt-5-mini-2025-08-07"
        log.info(f"No model name provided, using default model: {model_name}")

    # prepare output paths
    base_dir = Path(OUTPUTS_DIR, WORD_POSITION_DIR, story, "incontext", model_name)
    base_dir.mkdir(parents=True, exist_ok=True)
    path_responses_raw = base_dir / "responses_raw.pkl"
    path_responses_parsed = base_dir / "ratings.csv"
    path_failed_lines = base_dir / "failed_lines.txt"
    path_rating_reasons = base_dir / "rating_reasons.txt"

    # back up old parsed responses
    if path_responses_parsed.exists():
        path_responses_parsed_backup = base_dir / "ratings.backup.csv"
        if path_responses_parsed_backup.exists():
            raise FileExistsError(
                f"Backup file {path_responses_parsed_backup} already exists."
                " Delete it to continue."
            )

        shutil.copy(path_responses_parsed, path_responses_parsed_backup)
        log.info(f"Backed up old parsed responses to {path_responses_parsed_backup}")

    # back up old failed lines
    if path_failed_lines.exists():
        path_failed_lines_backup = base_dir / "failed_lines.backup.txt"
        if path_failed_lines_backup.exists():
            raise FileExistsError(
                f"Backup file {path_failed_lines_backup} already exists."
                " Delete it to continue."
            )
        shutil.copy(path_failed_lines, path_failed_lines_backup)
        log.info(f"Backed up old failed lines to {path_failed_lines_backup}")

    # back up old rating reasons
    if path_rating_reasons.exists():
        path_rating_reasons_backup = base_dir / "rating_reasons.backup.txt"
        if path_rating_reasons_backup.exists():
            raise FileExistsError(
                f"Backup file {path_rating_reasons_backup} already exists."
                " Delete it to continue."
            )
        shutil.copy(path_rating_reasons, path_rating_reasons_backup)
        log.info(f"Backed up old rating reasons to {path_rating_reasons_backup}")

    # Need raw responses
    assert path_responses_raw.exists()
    responses_raw: list[Response] = pickle.load(path_responses_raw.open("rb"))
    assert isinstance(responses_raw, list)
    assert all(isinstance(response, Response) for response in responses_raw)
    log.info(
        f"Loaded {len(responses_raw)} preexisting responses from {path_responses_raw}"
    )

    word_regex = re.compile(r"<w>(.*)</w>")
    section_id_regex = re.compile(r"<s>(.*)</s>")
    section_score_regex = re.compile(r"<r>(.*)</r>")
    alt_section_score_regex = re.compile(r"</r>(.*)</r>")
    n_sections = get_n_sections(story=story, word_position_mode="not sentences :)")

    rated_words_and_sections_dct: dict[str, list] = dict()
    # word, section_id, section_score
    failed_lines: list[str] = list()
    for response in responses_raw:
        rated_words_and_sections_dct, failed_lines_batch = parse_incontext_response(
            response=response,
            word_regex=word_regex,
            section_id_regex=section_id_regex,
            section_score_regex=section_score_regex,
            alt_section_score_regex=alt_section_score_regex,
            n_sections=n_sections,
            rated_words_and_sections_dct=rated_words_and_sections_dct,
        )
        failed_lines.extend(failed_lines_batch)

    # save data
    log.info("Saving data.")

    # check for missing ratings
    words_missing_ratings: set[str] = set()
    for word, ratings in rated_words_and_sections_dct.items():
        if -1 in ratings:
            words_missing_ratings.add(word)
    log.info(f"Found {len(words_missing_ratings)} words with missing ratings:")
    print(words_missing_ratings)

    pd.DataFrame.from_dict(
        rated_words_and_sections_dct,
        orient="index",
        columns=list(range(1, n_sections + 1)),  # type: ignore
    ).to_csv(path_responses_parsed, index=True)
    log.info(
        f"Saved {len(rated_words_and_sections_dct)}"
        f" rated words and sections to {path_responses_parsed}"
    )

    path_failed_lines.write_text("\n".join(failed_lines))
    log.info(f"Saved {len(failed_lines)} failed lines to {path_failed_lines}")

    # save rating reasons
    rating_reasons: list[str] = list()
    for response in responses_raw:
        rating_reasons.extend(response.output_text.split("\n"))
    path_rating_reasons.write_text("\n".join(rating_reasons))
    log.info(f"Saved {len(rating_reasons)} rating reasons to {path_rating_reasons}")


def rate_word_position_incontext(
    story: str,
    model_name: Optional[str] = None,
    batch_size: Optional[int] = None,
):
    # load words
    words = list(
        set(
            [
                word.strip()
                for word in load_words(config={"story": story}, corrections=True)
            ]
        )
    )

    # basic word cleanup
    words = [
        word for word in words if (word != "" and len(word) < 30) and ("," not in word)
    ]

    # load model
    env_file = dotenv_values(".env")
    api_key = env_file["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
    if model_name is None:
        model_name = "gpt-5-mini-2025-08-07"
        log.info(f"No model name provided, using default model: {model_name}")
    if batch_size is None:
        batch_size = 45
        log.info(f"No batch size provided, using default batch size: {batch_size}")

    # load prompts
    instruction_prompt = Path(
        DATA_DIR,
        "prompts",
        "word_position",
        story,
        "incontext",
        "instructions.txt",
    ).read_text()
    input_prompt = Path(
        DATA_DIR,
        "prompts",
        "word_position",
        story,
        "incontext",
        "input.txt",
    ).read_text()

    # register keyboard interrupt in all cases
    signal.signal(signal.SIGINT, signal.default_int_handler)

    # prepare output paths
    base_dir = Path(OUTPUTS_DIR, WORD_POSITION_DIR, story, "incontext", model_name)
    base_dir.mkdir(parents=True, exist_ok=True)
    path_responses_raw = base_dir / "responses_raw.pkl"
    path_responses_parsed = base_dir / "ratings.csv"
    path_failed_lines = base_dir / "failed_lines.txt"

    # if files already exist, load them
    responses_raw: list[Response] = list()
    if path_responses_raw.exists():
        responses_raw = pickle.load(path_responses_raw.open("rb"))
        assert isinstance(responses_raw, list)
        assert all(isinstance(response, Response) for response in responses_raw)
        log.info(
            f"Loaded {len(responses_raw)} preexisting"
            f" responses from {path_responses_raw}"
        )

    rated_words_and_sections_dct: dict[str, list] = dict()
    # word, section_id, section_score
    rated_words = set()
    if path_responses_parsed.exists():
        responses_parsed_df = pd.read_csv(path_responses_parsed, index_col=0)
        rated_words_and_sections_dct = {
            row[0]: list(row[1:]) for row in responses_parsed_df.itertuples()
        }
        log.info(f"Loaded preexisting parsed responses from {path_responses_parsed}")

        words_missing_ratings_previous: set[str] = set()
        for word, ratings in rated_words_and_sections_dct.items():
            if -1 in ratings:
                words_missing_ratings_previous.add(word)
        rated_words_and_sections_dct = {
            word: ratings
            for word, ratings in rated_words_and_sections_dct.items()
            if word not in words_missing_ratings_previous
        }

        # remove words that are already rated
        rated_words = set(rated_words_and_sections_dct.keys())
        words = list(set(words).difference(rated_words))
        log.info(f"Removed {len(rated_words)} words that are already rated")
        log.info(f"Remaining {len(words)} words to rate")

    failed_lines: list[str] = list()
    if path_failed_lines.exists():
        failed_lines = path_failed_lines.read_text().split("\n")
        log.info(
            f"Loaded {len(failed_lines)} preexisting failed"
            f" lines from {path_failed_lines}"
        )

    # shuffle words to avoid bias from sorted list
    rng = np.random.default_rng(seed=42)
    rng.shuffle(words)

    n_words = len(words)
    n_batches = math.ceil(n_words / batch_size)
    n_sections = get_n_sections(story=story, word_position_mode="none")

    word_regex = re.compile(r"<w>(.*)</w>")
    section_id_regex = re.compile(r"<s>(.*)</s>")
    section_score_regex = re.compile(r"<r>(.*)</r>")
    alt_section_score_regex = re.compile(r"</r>(.*)</r>")

    run_input_tokens = 0
    run_output_tokens = 0

    try:
        for batch_idx in tqdm(range(n_batches), desc="Processing batches"):
            min_idx = batch_idx * batch_size
            max_idx = min(min_idx + batch_size, n_words)
            words_batch = "\n".join(words[min_idx:max_idx])
            input_batch = input_prompt.replace("{words}", words_batch)
            response = client.responses.create(
                model=model_name,
                instructions=instruction_prompt,
                input=input_batch,
                store=False,
            )
            responses_raw.append(response)

            # log tokens
            run_input_tokens += (
                response.usage.input_tokens if response.usage is not None else 0
            )
            run_output_tokens += (
                response.usage.output_tokens if response.usage is not None else 0
            )
            rated_words_and_sections_dct, failed_lines_batch = parse_incontext_response(
                response=response,
                word_regex=word_regex,
                section_id_regex=section_id_regex,
                section_score_regex=section_score_regex,
                alt_section_score_regex=alt_section_score_regex,
                n_sections=n_sections,
                rated_words_and_sections_dct=rated_words_and_sections_dct,
            )
            failed_lines.extend(failed_lines_batch)

    except KeyboardInterrupt:
        log.critical("KeyboardInterrupt, saving data.")
    except Exception as err:
        log.critical(err)
    finally:
        # save data
        log.info("Saving data.")
        pickle.dump(responses_raw, path_responses_raw.open("wb"))
        log.info(f"Saved {len(responses_raw)} raw responses to {path_responses_raw}")

        # check for missing ratings
        words_missing_ratings: set[str] = set()
        for word, ratings in rated_words_and_sections_dct.items():
            if -1 in ratings:
                words_missing_ratings.add(word)
        log.info(f"Found {len(words_missing_ratings)} words with missing ratings:")
        print(words_missing_ratings)

        pd.DataFrame.from_dict(
            rated_words_and_sections_dct,
            orient="index",
            columns=list(range(1, n_sections + 1)),  # type: ignore
        ).to_csv(path_responses_parsed, index=True)
        log.info(
            f"Saved {len(rated_words_and_sections_dct)}"
            f" rated words and sections to {path_responses_parsed}"
        )
        n_new_successful_ratings = (
            len(rated_words_and_sections_dct)
            - len(words_missing_ratings)
            - len(rated_words)  # old words
        )
        n_successful_ratings = len(rated_words_and_sections_dct) - len(
            words_missing_ratings
        )

        path_failed_lines.write_text("\n".join(failed_lines))
        log.info(f"Saved {len(failed_lines)} failed lines to {path_failed_lines}")

        # save rating reasons
        rating_reasons: list[str] = list()
        for response in responses_raw:
            rating_reasons.extend(response.output_text.split("\n"))
        path_rating_reasons = base_dir / "rating_reasons.txt"
        path_rating_reasons.write_text("\n".join(rating_reasons))
        log.info(f"Saved {len(rating_reasons)} rating reasons to {path_rating_reasons}")

        # output tokens & cost
        log.info(f"Run input tokens: {run_input_tokens}")
        log.info(f"Run output tokens: {run_output_tokens}")
        total_input_tokens = 0
        total_output_tokens = 0
        for response in responses_raw:
            total_input_tokens += (
                response.usage.input_tokens if response.usage is not None else 0
            )
            total_output_tokens += (
                response.usage.output_tokens if response.usage is not None else 0
            )
        log.info(f"Total input tokens: {total_input_tokens}")
        log.info(f"Total output tokens: {total_output_tokens}")

        for table_model_name, prices in PRICES_DOLLAR_PER_MILLION_TOKENS.items():
            if table_model_name in model_name:
                input_cost = run_input_tokens * prices["input"] / 1000000
                output_cost = run_output_tokens * prices["output"] / 1000000
                total_cost = input_cost + output_cost
                log.info(f"Run cost: {round(total_cost, 2):.2f}$")
                if n_new_successful_ratings > 0:
                    log.info(
                        "Run cost per 1000 successful ratings: "
                        f"{round(total_cost / n_new_successful_ratings * 1000, 2):.2f}$"
                    )
                total_cost = (
                    total_input_tokens * prices["input"] / 1000000
                    + total_output_tokens * prices["output"] / 1000000
                )
                log.info(f"Total cost: {round(total_cost, 2):.2f}$")
                if n_successful_ratings > 0:
                    log.info(
                        "Total cost per 1000 successful ratings:"
                        f" {round(total_cost / n_successful_ratings * 1000, 2):.2f}$"
                    )
                break


def rate_word_position_incontext_top2(
    story: str,
    model_name: Optional[str] = None,
    batch_size: Optional[int] = None,
):
    word_regex = re.compile(r"<w>(.*)</w>")
    section1_regex = re.compile(r"<s1>(.*)</s1>")
    section2_regex = re.compile(r"<s2>(.*)</s2>")

    # load words
    words = list(set([word.strip() for word in load_words(corrections=True)]))

    # load model
    env_file = dotenv_values(".env")
    api_key = env_file["OPENAI_API_KEY"]
    client = OpenAI(api_key=api_key)
    if model_name is None:
        model_name = "gpt-5-mini-2025-08-07"
        log.info(f"No model name provided, using default model: {model_name}")
    if batch_size is None:
        batch_size = 300
        log.info(f"No batch size provided, using default batch size: {batch_size}")

    # load prompts
    instruction_prompt = Path(
        DATA_DIR,
        "prompts",
        "word_position",
        story,
        "incontext_top2",
        "instructions.txt",
    ).read_text()
    input_prompt = Path(
        DATA_DIR,
        "prompts",
        "word_position",
        story,
        "incontext_top2",
        "input.txt",
    ).read_text()

    # register keyboard interrupt in all cases
    signal.signal(signal.SIGINT, signal.default_int_handler)

    # prepare output paths
    base_dir = Path(OUTPUTS_DIR, WORD_POSITION_DIR, story, "incontext_top2", model_name)
    base_dir.mkdir(parents=True, exist_ok=True)
    path_responses_raw = base_dir / "responses_raw.pkl"
    path_responses_parsed = base_dir / "ratings.csv"
    path_failed_lines = base_dir / "failed_lines.txt"

    # if files already exist, load them
    responses_raw: list[Response] = list()
    if path_responses_raw.exists():
        responses_raw = pickle.load(path_responses_raw.open("rb"))
        assert isinstance(responses_raw, list)
        assert all(isinstance(response, Response) for response in responses_raw)
        log.info(
            f"Loaded {len(responses_raw)} preexisting"
            f" responses from {path_responses_raw}"
        )

    responses_parsed: list[tuple[str, int, int]] = list()
    if path_responses_parsed.exists():
        responses_parsed_df = pd.read_csv(path_responses_parsed)
        responses_parsed = [tuple(row[1:]) for row in responses_parsed_df.itertuples()]
        log.info(f"Loaded preexisting parsed responses from {path_responses_parsed}")

        # remove words that are already rated
        rated_words = set([word for word, _, _ in responses_parsed])
        words = list(set(words).difference(rated_words))
        log.info(f"Removed {len(rated_words)} words that are already rated")
        log.info(f"Remaining {len(words)} words to rate")

    failed_lines: list[str] = list()
    if path_failed_lines.exists():
        failed_lines = path_failed_lines.read_text().split("\n")
        log.info(
            f"Loaded {len(failed_lines)} preexisting failed"
            f" lines from {path_failed_lines}"
        )

    # shuffle words to avoid bias from sorted list
    rng = np.random.default_rng(seed=42)
    rng.shuffle(words)

    n_words = len(words)
    n_batches = math.ceil(n_words / batch_size)

    try:
        for batch_idx in tqdm(range(n_batches), desc="Processing batches"):
            min_idx = batch_idx * batch_size
            max_idx = min(min_idx + batch_size, n_words)
            words_batch = "\n".join(words[min_idx:max_idx])
            input_batch = input_prompt.replace("{words}", words_batch)
            response = client.responses.create(
                model=model_name,
                instructions=instruction_prompt,
                input=input_batch,
                store=False,
            )
            responses_raw.append(response)
            for line in response.output_text.split("\n"):
                try:
                    word = word_regex.search(line)
                    section1 = section1_regex.search(line)
                    section2 = section2_regex.search(line)
                    if word is None or section1 is None or section2 is None:
                        failed_lines.append(line)
                        continue
                    responses_parsed.append(
                        (
                            str(word.group(1)),
                            int(section1.group(1)),
                            int(section2.group(1)),
                        )
                    )
                except Exception as err:
                    failed_lines.append(line)
                    log.error(f"Error parsing line: {line} - {err}")
                    continue

    except KeyboardInterrupt:
        log.critical("KeyboardInterrupt, saving data.")
    except Exception as err:
        log.critical(err)
    finally:
        # save data
        log.info("Saving data.")
        pickle.dump(responses_raw, path_responses_raw.open("wb"))
        log.info(f"Saved {len(responses_raw)} raw responses to {path_responses_raw}")

        pd.DataFrame(responses_parsed, columns=["word", "section1", "section2"]).to_csv(  # type: ignore
            path_responses_parsed, index=False
        )
        log.info(
            f"Saved {len(responses_parsed)} parsed responses to {path_responses_parsed}"
        )

        path_failed_lines.write_text("\n".join(failed_lines))
        log.info(f"Saved {len(failed_lines)} failed lines to {path_failed_lines}")

        # save rating reasons
        rating_reasons: list[str] = list()
        for response in responses_raw:
            rating_reasons.extend(response.output_text.split("\n"))
        path_rating_reasons = base_dir / "rating_reasons.txt"
        path_rating_reasons.write_text("\n".join(rating_reasons))
        log.info(f"Saved {len(rating_reasons)} rating reasons to {path_rating_reasons}")

        # save count of matching sections for each word
        count_words: list[tuple[str, int]] = list()
        for word, section1, section2 in responses_parsed:
            count_words.append((word, int(section1 != -1) + int(section2 != -1)))

        # save count of words
        output_path_count = Path(
            OUTPUTS_DIR,
            WORD_POSITION_DIR,
            story,
            "incontext",
            model_name,
            "count_matching_sections.csv",
        )
        check_make_dirs(output_path_count, verbose=False)
        pd.DataFrame(count_words, columns=["word", "count"]).to_csv(  # type: ignore
            output_path_count,
            index=False,
        )
        log.info(f"Saved {len(count_words)} count of words to {output_path_count}")


def rate_word_position_exact_match(
    story: str,
    sentences: bool = False,
):
    # load story
    if sentences:
        section_texts = load_story_sentences(story, story_file="sectioned.txt")
    else:
        section_sentences = load_story_sentences_grouped(
            story, story_file="sectioned.txt"
        )
        section_texts = [
            "\n".join(section_sentences_) for section_sentences_ in section_sentences
        ]

    # load all words
    words = load_words(config={"story": story}, corrections=True)

    rated_words_last: list[tuple[str, Union[int, float]]] = list()
    rated_words_mean: list[tuple[str, Union[int, float]]] = list()
    rated_words_first: list[tuple[str, Union[int, float]]] = list()
    rated_words_all_matches: list[tuple[str, str]] = list()
    count_words: list[tuple[str, int]] = list()
    for word in words:
        if word == "":
            continue
        word_re = re.compile(r"\b(" + re.escape(word) + r")\b", flags=re.IGNORECASE)

        # last
        word_section_index = -1
        for section_idx, section_text in enumerate(section_texts):
            match = word_re.search(section_text)
            if match is not None:
                word_section_index = section_idx

        rated_words_last.append((word, word_section_index))

        # mean & all_matches
        word_section_indices = list()
        for section_idx, section_text in enumerate(section_texts):
            match = word_re.search(section_text)
            if match is not None:
                word_section_indices.append(section_idx)
        if len(word_section_indices) == 0:
            word_section_index = -1
            all_matches = ""
        else:
            word_section_index = np.mean(word_section_indices).item()
            all_matches = ",".join(map(str, word_section_indices))
        rated_words_mean.append((word, word_section_index))
        rated_words_all_matches.append((word, all_matches))

        # first
        word_section_index = -1
        for section_idx, section_text in enumerate(section_texts):
            match = word_re.search(section_text)
            if match is not None:
                word_section_index = section_idx
                break

        rated_words_first.append((word, word_section_index))

        # I know it's not efficient, but readability/lower complexity wins
        # count number of sections matching word
        count_sections = 0
        for section_text in section_texts:
            match = word_re.search(section_text)
            if match is not None:
                count_sections += 1
        count_words.append((word, count_sections))

    # save ratings
    if sentences:
        mode = "exact_match_sentences"
    else:
        mode = "exact_match"

    for model_name, rated_words in [
        ("last", rated_words_last),
        ("mean", rated_words_mean),
        ("first", rated_words_first),
        ("all_matches", rated_words_all_matches),
    ]:
        output_path = Path(
            OUTPUTS_DIR,
            WORD_POSITION_DIR,
            story,
            mode,
            model_name,
            "ratings.csv",
        )
        check_make_dirs(output_path, verbose=False)
        pd.DataFrame(rated_words, columns=["word", "section_index"]).to_csv(  # type: ignore
            output_path,
            index=False,
        )
        log.info(f"Saved {len(rated_words)} rated words to {output_path}")

    # save count of words
    output_path_count = Path(
        OUTPUTS_DIR,
        WORD_POSITION_DIR,
        story,
        mode,
        "count_matching_sections.csv",
    )
    check_make_dirs(output_path_count, verbose=False)
    pd.DataFrame(count_words, columns=["word", "count"]).to_csv(  # type: ignore
        output_path_count,
        index=False,
    )
    log.info(f"Saved {len(count_words)} count of words to {output_path_count}")


def rate_word_position(
    method: str,
    story: str,
    section_aggregation: Optional[str] = None,
    model_name: Optional[str] = None,
    batch_size: int = 300,
    reprocess_raw_responses: bool = False,
):
    # save & print config
    if method == "embeddings":
        # Why do embeddings not work well?
        # For each word, the cosine similarity with an embedding may not focus on the
        # most relevant aspect. For instance take the word "fish". Although the 4th
        # section multiple times mentions "fish" and "fishing", the correlation is way
        # lower than with sentences such as "I can see the men out there." or
        # "I look at the creek." correlation & cosine similarity behave similarly here.
        rate_word_position_embeddings_example(
            model_name=model_name,
            section_aggregation=section_aggregation,
        )
        raise ValueError(
            f"{method=} doesn't work well. Look into the code for details."
        )
    elif method == "reranker":
        # "cross-encoder/stsb-roberta-large" seems to work best.
        # the model still has weird ratings (e.g. "fish" and "He says a prayer for us,
        # the living, and when he finishes, he says a prayer for the soul of the
        # departed." -> higher than fish related sentences....)
        rate_word_position_reranker(
            story=story,
            model_name=model_name,
            section_aggregation=section_aggregation,
        )
        raise ValueError(
            f"{method=} doesn't work well. Look into the code for details."
        )
    elif method == "themesim":
        rate_word_position_themesim(
            story=story,
            section_aggregation=section_aggregation,
        )
    elif method == "incontext":
        if reprocess_raw_responses:
            word_position_incontext_reprocess(
                story=story,
                model_name=model_name,
                batch_size=batch_size,
            )
        else:
            rate_word_position_incontext(
                story=story,
                model_name=model_name,
                batch_size=batch_size,
            )
    elif method == "incontext_top2":
        rate_word_position_incontext_top2(
            story=story,
            model_name=model_name,
            batch_size=batch_size,
        )
    elif method.startswith("exact_match"):
        sentences = False
        if method == "exact_match_sentences":
            sentences = True
        rate_word_position_exact_match(
            story=story,
            sentences=sentences,
        )
    else:
        raise ValueError(f"Invalid {method=}")


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument(
        "-m",
        "--method",
        type=str,
        default="exact_match",
        choices=[
            "embeddings",
            "reranker",
            "themesim",
            "incontext",
            "incontext_top2",
            "exact_match",
            "exact_match_sentences",
        ],
        help="Which method to use for rating word position.",
    )
    args.add_argument(
        "-M",
        "--model_name",
        type=str,
        default=None,
        help=(
            "Which model to use for rating word position"
            " [Optional for embeddings, reranker, incontext, incontext_top2]."
        ),
    )
    args.add_argument(
        "-s",
        "--story",
        type=str,
        default="carver_original",
        help="Which story to use for rating word position.",
    )
    args.add_argument(
        "-a",
        "--section_aggregation",
        type=str,
        default=None,
        choices=["mean", "max", "top3"],
        help=(
            "How to aggregate within-section similarity scores."
            " [Optional for embeddings, reranker, themesim]."
        ),
    )
    args.add_argument(
        "-b",
        "--batch_size",
        type=int,
        default=None,
        help=(
            "Number of words rated in one batch."
            " [Optional for incontext, incontext_top2]"
        ),
    )
    args.add_argument(
        "--reprocess-raw-responses",
        action="store_true",
        help=(
            "Reprocess raw responses for incontext method."
            " E.g. if the parser had a bug."
        ),
    )
    args = args.parse_args()
    rate_word_position(
        method=args.method,
        story=args.story,
        model_name=args.model_name,
        section_aggregation=args.section_aggregation,
        batch_size=args.batch_size,
        reprocess_raw_responses=args.reprocess_raw_responses,
    )
