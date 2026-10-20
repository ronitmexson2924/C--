"""Fuzzy suggestion and edit-distance helpers for C-- diagnostics per §7."""

from typing import Iterable, Optional


def damerau_levenshtein(s1: str, s2: str) -> int:
    """Compute the Damerau-Levenshtein distance between two strings.

    Accounts for insertions, deletions, substitutions, and transpositions
    of adjacent characters.
    """
    if s1 == s2:
        return 0

    len1, len2 = len(s1), len(s2)
    d: dict[tuple[int, int], int] = {}

    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1

    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,        # deletion
                d[(i, j - 1)] + 1,        # insertion
                d[(i - 1, j - 1)] + cost,  # substitution
            )
            if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + 1)  # transposition

    dist = d[(len1 - 1, len2 - 1)]

    # Case-only differences count as distance 1 per §7
    if s1.lower() == s2.lower() and s1 != s2:
        dist = min(dist, 1)

    return dist


def find_suggestion(target: str, candidates: Iterable[str]) -> Optional[str]:
    """Find the best matching candidate within acceptable edit distance per §7.

    Rules:
    - distance <= 2 for strings of length >= 5.
    - distance <= 1 for strings of length < 5.
    - Case-only differences count as distance 1.
    - Ties broken alphabetically.
    """
    if not target:
        return None

    max_dist = 1 if len(target) < 5 else 2
    best_candidate: Optional[str] = None
    best_dist = max_dist + 1

    unique_candidates = sorted(set(candidates))

    for cand in unique_candidates:
        if cand == target:
            continue
        dist = damerau_levenshtein(target, cand)
        if dist <= max_dist:
            if dist < best_dist:
                best_dist = dist
                best_candidate = cand
            elif dist == best_dist:
                if best_candidate is None or cand < best_candidate:
                    best_candidate = cand

    return best_candidate
