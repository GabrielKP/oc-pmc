from typing import List, Dict


def load_word_list_txt(path: str) -> List[str]:
    """Loads file.txt in which each line is treated as a new word."""
    with open(path, "r") as f_in:
        lines = f_in.readlines()

    if lines[-1][-1] != "\n":
        raise ValueError("Only accept files with newline at the end.")

    return [line[:-1] for line in lines]


def import_words_from_txt(config: Dict[str, str]):
    words_to_rate = load_word_list_txt(config["path_words"])
    print(f"n words: {len(words_to_rate)}")

    lines = ["var words = [\n"]
    lines += [f'  {{ word: "{word}" }},' + "\n" for word in words_to_rate]
    lines.append("];\n")

    with open(config["path_words_var"], "w") as f_out:
        f_out.writelines(lines)


if __name__ == "__main__":
    config = {
        "path_words": "/Volumes/opt/ldata/words_to_rate/carver_original/2024-04-22-final_words_to_rate-suppress-toronto.txt",
        "path_words_var": "static/js/words_var.js",
    }
    import_words_from_txt(config)
