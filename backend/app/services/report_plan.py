"""Bound report generation work while keeping one selection-wide depth policy."""

from math import ceil

REPORT_WORD_LIMITS = {1: (600, 800), 2: (450, 650), 3: (350, 500), 4: (280, 400), 5: (220, 350)}
SECTION_WEIGHTS = (0.25, 0.10, 0.15, 0.10, 0.10, 0.15, 0.15, 0.08)


def batch_token_budget(sections: tuple[int, ...], maximum: int) -> int:
    return min(maximum, max(700, ceil(6000 * sum(SECTION_WEIGHTS[n - 1] for n in sections) / sum(SECTION_WEIGHTS))))


def section_batches(paper_count: int, maximum: int) -> list[tuple[int, ...]]:
    if paper_count <= 2:
        groups = [tuple(range(1, 9))]
    elif paper_count == 3:
        groups = [(1, 2, 3, 4), (5, 6, 7, 8)]
    else:
        groups = [(1, 2), (3, 4, 5), (6, 7, 8)]
    batches: list[tuple[int, ...]] = []
    for group in groups:
        pending: tuple[int, ...] = ()
        for number in group:
            if pending and batch_token_budget((*pending, number), 8192) > maximum:
                batches.append(pending)
                pending = ()
            pending = (*pending, number)
        if pending:
            batches.append(pending)
    return batches
