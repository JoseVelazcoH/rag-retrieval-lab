# docsearch

Find information in your documents without an LLM: BM25 + vector search,
fully local, instant, and every answer cites its exact source.

The point: for *finding* things in a pile of internal docs, you often do not
need a generative model. Retrieval alone gives you the passage, the file and
the line. No hallucinations, no API key, no GPU, no data leaving your machine.

## What it shows

The corpus (`docs/`) is 43 short English markdown files from a fictional company
(runbooks, auth, deploys, HR, security).

| Query | Method | Result |
| --- | --- | --- |
| `timeout 504 nginx` | BM25 | Exact keywords find `runbooks/nginx.md` |
| `the page takes forever and then crashes` | BM25 | Lost: no shared words with the answer |
| `the page takes forever and then crashes` | vector | Finds the same nginx runbook by meaning |
| `I can't log in with my token` | hybrid | RRF puts `auth/jwt.md` first; BM25 alone does not |

## Run it

Requires [uv](https://docs.astral.sh/uv/). PyTorch is installed from the CPU-only
wheel index (see `pyproject.toml`).

```bash
uv sync
uv run docsearch index            # chunk docs, build BM25 + embeddings into .index/
uv run search "timeout 504 nginx" --bm25
uv run search "the page takes forever and then crashes" --vector
uv run search "I can't log in with my token"       # hybrid is the default
```

Options: `--bm25`, `--vector`, `--hybrid`, `-k 3`.

The timer in the output covers the search itself. Loading the embedding model
(about a second) happens once per process, before the timer starts, and only for
`--vector` and `--hybrid`.

## How it works

```
src/docsearch/
  corpus.py        split markdown by paragraph, keep path + starting line
  text.py          lowercase, strip accents, small English stopword list
  bm25_index.py    BM25 via bm25s
  vector_index.py  cosine similarity as a dot product over normalized vectors
  encoder.py       BAAI/bge-small-en-v1.5 (query instruction prefix, no passage prefix)
  hybrid.py        Reciprocal Rank Fusion, k = 60
  engine.py        index building and search orchestration (lazy model load)
  render.py        rich output with highlighted snippets
  cli.py           typer commands
```

## Tests

```bash
uv run pytest
```

## Record the demo

[VHS](https://github.com/charmbracelet/vhs) renders `demo.tape` to `demo.mp4`
and `demo.gif` at 1080x1350 (4:5, vertical social format). VHS cannot set a
window title, so `add_title.sh` overlays a macOS-style one afterwards.

```bash
uv run docsearch index
vhs demo.tape
./add_title.sh   # needs uv (fetches Pillow on the fly)
```
