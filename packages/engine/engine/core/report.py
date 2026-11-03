"""What a people run did or would do: the words for a person, the numbers a test checks, the rows refused."""

from dataclasses import dataclass, field


@dataclass
class Report:
    """What a run did or would do. `lines` are the words for a person; `counts` are the numbers a test checks."""

    lines: list[str] = field(default_factory=list[str])
    counts: dict[str, int] = field(default_factory=dict[str, int])
    refused: list[str] = field(default_factory=list[str])

    def count(self, what: str, n: int = 1) -> None:
        self.counts[what] = self.counts.get(what, 0) + n

    def refuse(self, why: str) -> None:
        self.refused.append(why)
        self.count("refused")
