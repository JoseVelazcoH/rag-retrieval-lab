from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    path: str
    line: int
    text: str


@dataclass(frozen=True)
class Hit:
    chunk_id: int
    score: float
