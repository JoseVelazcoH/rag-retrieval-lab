import json
from pathlib import Path

from docsearch.constants import DEFAULT_INDEX_DIR
from docsearch.encoder import Encoder, silence_libraries
from docsearch.engine import Mode, SearchEngine

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "results"
MODES = (Mode.BM25, Mode.VECTOR, Mode.HYBRID)


def open_engine() -> SearchEngine:
    silence_libraries()
    engine = SearchEngine(ROOT / DEFAULT_INDEX_DIR, encoder_factory=Encoder)
    for mode in MODES:
        engine.warm_up(mode)
    return engine


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
