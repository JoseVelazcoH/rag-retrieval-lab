from pathlib import Path

DEFAULT_DOCS_DIR = Path("docs")
DEFAULT_INDEX_DIR = Path(".index")

BM25_SUBDIR = "bm25"
CHUNKS_FILE = "chunks.json"
VECTORS_FILE = "vectors.npy"

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
E5_MODEL = "intfloat/e5-small-v2"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
E5_QUERY_PREFIX = "query: "
E5_PASSAGE_PREFIX = "passage: "
EMBEDDING_BATCH_SIZE = 32
ENCODER_THREADS = 2

DEFAULT_TOP_K = 3
CANDIDATE_POOL_SIZE = 20
RRF_K = 60
WARM_UP_QUERY = "warm up"
WARM_UP_ROUNDS = 2

SNIPPET_MAX_LINES = 3
SNIPPET_MAX_ROWS = 5
SNIPPET_MAX_WIDTH = 51

STOPWORDS = frozenset(
    """
    a an and are as at be but by can for from has have i if in is it its my
    of on or so that the then there this to was we were what when will with
    you your s t
    """.split()
)
