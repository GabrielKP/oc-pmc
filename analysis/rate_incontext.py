import argparse
import math
import pickle
import re
import signal
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from dotenv import dotenv_values
from oc_pmc import DATA_DIR, OUTPUTS_DIR, get_logger
from oc_pmc.load import load_words
from openai import OpenAI
from openai.types.responses import Response
from tqdm import tqdm

APPROACH = "incontext"

log = get_logger(__name__)


def rate_incontext(
    story: str,
    prompt_name: Optional[str] = None,
    model_name: Optional[str] = None,
    batch_size: Optional[int] = None,
    path_words_to_rate: Optional[str] = None,
):
    word_regex = re.compile(r"<word>(.*)</word>")
    rating_regex = re.compile(r"<rating>(.*)</rating>")

    # load words
    if path_words_to_rate is None:
        words = list(set([word.strip() for word in load_words(corrections=True)]))
    else:
        words = list(
            set(
                [
                    word.strip()
                    for word in Path(path_words_to_rate).read_text().split("\n")
                ]
            )
        )
        log.info(f"Loaded {len(words)} words from {path_words_to_rate}")

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
        batch_size = 300
        log.info(f"No batch size provided, using default batch size: {batch_size}")

    # load prompts
    prompt_name_str = ""
    if prompt_name is not None and prompt_name != "":
        prompt_name_str = f"_{prompt_name}"
    instruction_prompt = Path(
        DATA_DIR,
        "prompts",
        "story_relatedness",
        story,
        f"instructions{prompt_name_str}.txt",
    ).read_text()
    input_prompt = Path(
        DATA_DIR, "prompts", "story_relatedness", story, "input.txt"
    ).read_text()

    # register keyboard interrupt in all cases
    signal.signal(signal.SIGINT, signal.default_int_handler)

    batch_size_str = f"_{batch_size}" if batch_size != 300 else ""

    # prepare output paths
    model_name_str = f"{model_name}{prompt_name_str}"
    base_dir = Path(OUTPUTS_DIR, "rated_words", "incontext", model_name_str, story)
    base_dir.mkdir(parents=True, exist_ok=True)
    path_responses_raw = base_dir / f"responses_raw{batch_size_str}.pkl"
    path_responses_parsed = base_dir / f"ratings{batch_size_str}.csv"
    path_failed_lines = base_dir / f"failed_lines{batch_size_str}.txt"
    path_reasons = base_dir / f"reasons{batch_size_str}.txt"

    # if files arleady exist, load them
    # raw responses
    responses_raw: list[Response] = list()
    if path_responses_raw.exists():
        responses_raw = pickle.load(path_responses_raw.open("rb"))
        assert isinstance(responses_raw, list)
        assert all(isinstance(response, Response) for response in responses_raw)
        log.info(
            f"Loaded {len(responses_raw)} preexisting"
            f" responses from {path_responses_raw}"
        )

    # parsed responses
    responses_parsed: list[tuple[str, int]] = list()
    if path_responses_parsed.exists():
        responses_parsed_df = pd.read_csv(path_responses_parsed)
        responses_parsed = [tuple(row[1:]) for row in responses_parsed_df.itertuples()]
        log.info(f"Loaded preexisting parsed responses from {path_responses_parsed}")

        # remove words that are already rated
        rated_words = set([str(word) for word, _ in responses_parsed])
        words = list(set(words).difference(rated_words))
        log.info(f"Removed {len(rated_words)} words that are already rated")
        log.info(f"Remaining {len(words)} words to rate")

    # failed lines
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
                store=True,
            )
            responses_raw.append(response)
            for line in response.output_text.split("\n"):
                try:
                    word = word_regex.search(line)
                    rating = rating_regex.search(line)
                    if word is None or rating is None:
                        failed_lines.append(line)
                        continue
                    responses_parsed.append(
                        (
                            str(word.group(1)),
                            int(rating.group(1)),
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
        log.info("Saving data.")

        # raw responses
        pickle.dump(responses_raw, path_responses_raw.open("wb"))
        log.info(f"Saved {len(responses_raw)} raw responses to {path_responses_raw}")

        # parsed responses
        # make sure they are unique
        responses_dct: dict[str, int] = dict()
        for word, rating in responses_parsed:
            if word not in responses_dct:
                responses_dct[word] = rating
            else:
                log.warning(
                    f"Duplicate word: {word}"
                    f" - first: {responses_dct[word]} - second: {rating}"
                )
        responses_parsed = list(responses_dct.items())
        pd.DataFrame(responses_parsed, columns=["word", "rating"]).to_csv(  # type: ignore
            path_responses_parsed, index=False
        )
        log.info(
            f"Saved {len(responses_parsed)} parsed responses to {path_responses_parsed}"
        )

        # failed lines
        path_failed_lines.write_text("\n".join(failed_lines))
        log.info(f"Saved {len(failed_lines)} failed lines to {path_failed_lines}")

        # reasons
        reasons = list()
        for response in responses_raw:
            reasons.extend(response.output_text.split("\n"))

        path_reasons.write_text("\n".join(reasons))
        log.info(f"Saved {len(reasons)} rating reasons to {path_reasons}")


if __name__ == "__main__":
    args = argparse.ArgumentParser()
    args.add_argument(
        "-s", "--story", type=str, default="carver_original", help="Story to rate."
    )
    args.add_argument(
        "-p", "--prompt_name", type=str, default=None, help="Name of the prompt to use."
    )
    args.add_argument(
        "-m", "--model_name", type=str, default=None, help="openai model to use."
    )
    args.add_argument(
        "-b",
        "--batch_size",
        type=int,
        default=None,
        help="How many words in one batch.",
    )
    args.add_argument(
        "-w",
        "--path_words_to_rate",
        type=str,
        default=None,
        help="Path to file with words to rate. If none, will rate all words.",
    )
    args = args.parse_args()
    rate_incontext(
        story=args.story,
        prompt_name=args.prompt_name,
        model_name=args.model_name,
        batch_size=args.batch_size,
        path_words_to_rate=args.path_words_to_rate,
    )
