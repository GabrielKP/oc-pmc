story = [
    "A friend of mine told me a sad story the other day about the neighbour of hers.",
    "He had begun a correspondence with a stranger through an online dating service.",
    "The friend lived hundreds of miles away, in North Carolina.",
    "The two men exchanged messages and then photos and were soon having long conversations, at first in writing and then by phone.",
    "They found that they had many interests in common, were emotionally and intellectually compatible, were comfortable with each other and were physically attracted to each other, as far as they could tell on the Internet.",
    "Their professional interests, too, were close, my friend’s neighbour being an accountant and his new friend down South an assistant professor of economics at a small college.",
    "After some months, they seemed to be well and truly in love, and my friend’s neighbour was convinced that ‘this was it’, as he put it.",
    "When some vacation time came up, he arranged to fly down south for a few days and meet his Internet love.",
    "***",
    "During the day of travel, he called his friend two or three times and they talked",
    "Then he was surprised to receive no answer.",
    "Nor was his friend at the airport to meet him.",
    "After waiting there and calling several more times, my friend’s neighbour left the airport and went to the address his friend had given him.",
    "No one answered when he knocked and rang.",
    "Every possibility went through his mind.",
    "***",
    "Here, some parts of the story are missing, but my friend told me that what her neighbour learned was that, on that very day, even as he was on his way south, his Internet friend had died of a heart attack while on the phone with his doctor;",
    "my friend’s neighbour, having learned this either from the man’s neighbour or from the police, had made his way to the local morgue;",
    "he had been allowed to view his Internet friend;",
    "and so it was here, face to face with a dead man, that he first laid eyes on the one who, he had been convinced, was to have been his companion for life.",
]

print("var story = {\n  row: [")
for idx, sen in enumerate(story):
    n_words = len(sen.split(" "))
    print(
        f'    {{ Story: "{sen}", order: "{idx}", num_char: "{len(sen)}", num_words: "{n_words}", section: "1" }},'
    )

print("  ],\n};")
