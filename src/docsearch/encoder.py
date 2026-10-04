import logging
import os
import warnings

import numpy as np

from docsearch.constants import (
    EMBEDDING_BATCH_SIZE,
    ENCODER_THREADS,
    EMBEDDING_MODEL,
    QUERY_PREFIX,
)


def silence_libraries() -> None:
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    warnings.filterwarnings("ignore")
    logging.disable(logging.WARNING)


def format_query(text: str) -> str:
    return QUERY_PREFIX + text


def format_passage(text: str) -> str:
    return text


class Encoder:
    """bge-small-en embeddings, L2-normalized so cosine is a dot product."""

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        silence_libraries()
        import torch
        from sentence_transformers import SentenceTransformer

        torch.set_num_threads(ENCODER_THREADS)

        try:
            self._model = SentenceTransformer(model_name, local_files_only=True)
        except OSError:
            self._model = SentenceTransformer(model_name)

    def encode_queries(self, texts: list[str]) -> np.ndarray:
        return self._encode([format_query(t) for t in texts])

    def encode_passages(self, texts: list[str]) -> np.ndarray:
        return self._encode([format_passage(t) for t in texts])

    def _encode(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(
            texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
