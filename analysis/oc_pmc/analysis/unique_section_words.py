import re

from oc_pmc.load import load_story


def get_unique_words_for_section(story: str, section_number: int) -> list[str]:
    """Returns all unique words for a given section.

    Parameters
    ----------
    story : str
        Name of the story to load.
    section_number : int
        Number of the section (1-based).

    Returns
    -------
    set[str]
        Set of unique words that appear only in the specified section.
    """
    text = load_story(story)
    sections = [s.strip() for s in text.split("***") if s.strip()]

    if section_number < 1 or section_number > len(sections):
        raise ValueError(
            f"Invalid {section_number=}. Story has {len(sections)} sections."
        )

    def get_words(text):
        # Convert to lowercase and extract words (letters only)
        words = re.findall(r"[a-zA-Z]+", text.lower())
        return set(words)

    # Get words for each section
    section_words = [get_words(section) for section in sections]

    # Get words from target section
    target_words = section_words[section_number - 1]

    # Get all words from other sections
    other_words = set()
    for i, words in enumerate(section_words):
        if i != section_number - 1:
            other_words.update(words)

    # Return unique words
    return list(target_words - other_words)


def get_uniquely_shared_words_for_sections(
    story: str, section_numbers: list[int]
) -> list[str]:
    """Returns words that appear in all given sections and in no other section.

    Parameters
    ----------
    story : str
        Name of the story to load.
    section_numbers : list[int]
        Section numbers (1-based). Words must appear in each of these sections
        and in no section outside this list.

    Returns
    -------
    list[str]
        Sorted list of uniquely shared words (in the given sections only).
    """
    if not section_numbers:
        return []

    text = load_story(story)
    sections = [s.strip() for s in text.split("***") if s.strip()]

    def get_words(text):
        words = re.findall(r"[a-zA-Z]+", text.lower())
        return set(words)

    section_words = [get_words(section) for section in sections]
    n_sections = len(sections)
    section_set = set(section_numbers)

    for num in section_numbers:
        if num < 1 or num > n_sections:
            raise ValueError(f"Invalid section {num}. Story has {n_sections} sections.")

    # Words that appear in all of the given sections
    shared = section_words[section_numbers[0] - 1].copy()
    for num in section_numbers[1:]:
        shared &= section_words[num - 1]

    # Remove words that appear in any other section
    for i in range(n_sections):
        if (i + 1) not in section_set:
            shared -= section_words[i]

    return sorted(shared)


def print_unique_section_words(text: str):
    sections = [s.strip() for s in text.split("***") if s.strip()]

    print(f"Found {len(sections)} sections\n")

    # Function to extract words from text
    def get_words(text):
        # Convert to lowercase and extract words (letters only)
        words = re.findall(r"[a-zA-Z]+", text.lower())
        return set(words)

    # Get words for each section
    section_words = [get_words(section) for section in sections]

    # Find unique words for each section
    for i, words in enumerate(section_words):
        # Get all words from other sections
        other_words = set()
        for j, other in enumerate(section_words):
            if i != j:
                other_words.update(other)

        unique = words - other_words
        unique_sorted = sorted(unique, key=lambda x: (-len(x), x))

        print(f"=== SECTION {i + 1} ===")
        print(f"Total unique words: {len(unique)}")
        print(f"First 20 unique words: {unique_sorted[:20]}")
        print()


if __name__ == "__main__":
    story = "carver_original"
    text = load_story(story)
    print_unique_section_words(text)

    unique_words = get_unique_words_for_section(story, 1)
    print("\nUnique words for section 1:")
    print(unique_words)

    shared_sections = [3, 5, 7]
    shared_words = get_uniquely_shared_words_for_sections(story, shared_sections)
    print(f"\nUniquely shared words for sections {shared_sections}:")
    print(shared_words)
