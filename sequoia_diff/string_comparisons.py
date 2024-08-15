import difflib


def levenshtein_distance(s1: str | None, s2: str | None) -> int:
    if s1 is None:
        s1 = ""
    if s2 is None:
        s2 = ""

    if len(s1) < len(s2):
        s1, s2 = s2, s1

    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def normalized_levenshtein_distance(s1: str | None, s2: str | None) -> float:
    if s1 is None:
        s1 = ""
    if s2 is None:
        s2 = ""

    levenshtein_dist = levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 0.0

    return levenshtein_dist / max_len


def generate_trigrams(s: str) -> list[str]:
    """Generate tri-grams for a given string."""
    if len(s) < 3:
        return [
            s
        ]  # If the string is shorter than 3 characters, use the string itself as the only trigram
    return [s[i : i + 3] for i in range(len(s) - 2)]


def normalized_tri_gram_distance(a: str | None, b: str | None) -> float:
    if a is None:
        a = ""
    if b is None:
        b = ""

    trigrams1 = generate_trigrams(a)
    trigrams2 = generate_trigrams(b)

    matcher = difflib.SequenceMatcher(None, trigrams1, trigrams2)
    similarity_ratio = matcher.ratio()

    return 1.0 - similarity_ratio  # Distance is 1 - similarity ratio


def tri_gram_distance(a: str | None, b: str | None) -> int:
    if a is None:
        a = ""
    if b is None:
        b = ""

    trigrams1 = generate_trigrams(a)
    trigrams2 = generate_trigrams(b)

    matcher = difflib.SequenceMatcher(None, trigrams1, trigrams2)
    matches = sum(n for _, _, n in matcher.get_matching_blocks())
    total_trigrams = len(trigrams1) + len(trigrams2)

    return total_trigrams - 2 * matches
