import random
import sys
from copy import copy
from typing import List

N_WORDS_TOTAL = 6754


def generate_permutation(n_ratings_per_word=10):

    # generate orders
    word_order = list(range(N_WORDS_TOTAL))
    orders: List[List[int]] = list()
    for _ in range(n_ratings_per_word):
        word_order = random.sample(word_order, k=len(word_order))
        orders.append(copy(word_order))

    # save as javascript list
    formatted = [f"[{','.join((str(x) for x in perm))}]" for perm in orders]
    line = f"var permutations = [{','.join(formatted)}];"

    with open("static/js/permutations_var.js", "w") as f_out:
        f_out.write(line + "\n")

    return 0


if __name__ == "__main__":
    if len(sys.argv) == 2:
        generate_permutation(int(sys.argv[1]))
    else:
        generate_permutation()
