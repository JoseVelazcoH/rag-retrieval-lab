<h1 align="center">RAG Retrieval Lab</h1>

<p align="center">
  <b>Measure what actually improves retrieval before you change your RAG</b>
</p>
<p align="center">
  A local search engine (BM25, embeddings and hybrid) plus the experiments that tested common RAG advice on public data, with the hypothesis written before every run.
</p>

<div align="center">

  <img src="https://img.shields.io/badge/Type-Research%20Lab-FFD803?style=for-the-badge&labelColor=272343" alt="Type" />
  <img src="https://img.shields.io/badge/Stack-Python%20%7C%20bm25s%20%7C%20Sentence%20Transformers-FFD803?style=for-the-badge&labelColor=272343" alt="Stack" />
  <img src="https://img.shields.io/badge/Runs-Local%20%7C%20CPU%20only-FFD803?style=for-the-badge&labelColor=272343" alt="Runs locally on CPU" />

</div>

<p align="center">
  <img src="demo.gif" width="70%" alt="docsearch demo" />
</p>

<details open>
  <summary><h2>Table of Contents</h2></summary>
  <ol>
    <li><a href="#the-problem">➤ The Problem</a></li>
    <li><a href="#key-findings">➤ Key Findings</a></li>
    <li><a href="#what-we-measured">➤ What We Measured</a></li>
    <li><a href="#datasets">➤ Datasets</a></li>
    <li><a href="#methodology">➤ Methodology</a></li>
    <li><a href="#folder-structure">➤ Folder Structure</a></li>
    <li><a href="#getting-started">➤ Getting Started</a></li>
    <li><a href="#reproduce-the-experiments">➤ Reproduce the Experiments</a></li>
    <li><a href="#limitations">➤ Limitations</a></li>
    <li><a href="#references">➤ References</a></li>
  </ol>
</details>

![-----](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## <img src="https://api.iconify.design/lucide/telescope.svg?color=%23E4A700" width="20" height="20">&nbsp; The Problem

Most RAG advice comes as a list of techniques with no numbers attached.

<table width="100%">
  <tr>
    <td width="33%" valign="top" align="center">
      <br>
      <h3 align="center"><img src="https://api.iconify.design/lucide/scissors.svg?color=%23E4A700" width="18" height="18">&nbsp; Arbitrary Chunks</h3>
      <p align="center">Documents are cut every N tokens, so a chunk can start mid-sentence without the heading that says what it is about.</p>
      <br>
    </td>
    <td width="33%" valign="top" align="center">
      <br>
      <h3 align="center"><img src="https://api.iconify.design/lucide/message-square-dashed.svg?color=%23E4A700" width="18" height="18">&nbsp; Advice Without Data</h3>
      <p align="center">Hybrid search and rerankers are recommended everywhere, usually without a reproducible measurement.</p>
      <br>
    </td>
    <td width="33%" valign="top" align="center">
      <br>
      <h3 align="center"><img src="https://api.iconify.design/lucide/eye-off.svg?color=%23E4A700" width="18" height="18">&nbsp; Silent Failures</h3>
      <p align="center">When retrieval sends the wrong chunks, the LLM still writes a fluent answer, so the error looks like a hallucination.</p>
      <br>
    </td>
  </tr>
</table>

![-----](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## <img src="https://api.iconify.design/lucide/lightbulb.svg?color=%23E4A700" width="20" height="20">&nbsp; Key Findings

1. **Split your documents at the headings.** On the Kubernetes and PostgreSQL docs, section-based chunks put the right passage in the top 3 for 72% of questions on average, against 63% for fixed 200-word windows. They also beat fixed windows of the same average size, so the gain comes from the headings and not from smaller chunks.
2. **Chunking mattered more than the embedding model.** Swapping bge-small for e5-small moved recall@3 by about 2 points. Splitting at headings moved it by about 9.
3. **Hybrid search and a small reranker did not beat embeddings alone** on two public benchmarks. Hybrid search clearly beat BM25 alone, but not vector search.

> These results hold for the data, models and questions described below. Measure on your own documents before adopting any of them.

![-----](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## <img src="https://api.iconify.design/lucide/flask-conical.svg?color=%23E4A700" width="20" height="20">&nbsp; What We Measured

### Chunking: where chunks begin

Vector search, recall@3 (the answer quote is inside one of the top 3 chunks). Significance is a paired sign test on the questions where the two variants disagree.

| **Doc set / model**       | **Fixed 200 words** | **Fixed 120 words** | **Split at headings** | **Headings vs fixed 200** |
| :------------------------ | :-----------------: | :-----------------: | :-------------------: | :------------------------ |
| Kubernetes / bge-small    | 64%                 | 62%                 | **73%**               | 55 vs 27, p = 0.003       |
| Kubernetes / e5-small     | 65%                 | 67%                 | **73%**               | 47 vs 23, p = 0.006       |
| PostgreSQL / bge-small    | 63%                 | 64%                 | **69%**               | 47 vs 31, p = 0.09        |
| PostgreSQL / e5-small     | 60%                 | 65%                 | **72%**               | 56 vs 19, p < 0.001       |

The pre-registered hypothesis required a significant win in all four setups. It held in three. PostgreSQL with bge-small pointed the same way without reaching significance. Adding a `Doc > Section` breadcrumb to each chunk, or stripping the markdown, made no significant difference.

### Retrieval method: BM25, embeddings, hybrid and reranking

BEIR test splits, recall@3. The vector model is bge-small, the reranker is `cross-encoder/ms-marco-MiniLM-L-6-v2` over the vector top 20.

| **Mode**                 | **SciFact (300 q)** | **CQADupStack Android (699 q)** | **Search time** |
| :----------------------- | :-----------------: | :-----------------------------: | :-------------- |
| BM25                     | 69%                 | 43%                             | under 1 ms      |
| Vector                   | 72%                 | 53%                             | ~55 ms          |
| Hybrid (RRF, equal)      | 73%                 | 51%                             | ~70 ms          |
| Hybrid (RRF, 70/30)      | 74%                 | 53%                             | ~70 ms          |
| Vector + reranker        | 73%                 | 51%                             | 2 to 3 s        |

None of hybrid, weighted hybrid or reranking beat vector search alone with a significant sign test on either dataset. A follow-up that split Android queries into "contains an identifier" and "natural language" (rule fixed before running) did not find a hybrid advantage on identifier queries either.

Every number above comes from the JSON files in [`results/`](results/), except the reranker row, which comes from an earlier run. Rerun `beir_eval.py` with `--rerank` to regenerate it.

![-----](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## <img src="https://api.iconify.design/lucide/database.svg?color=%23E4A700" width="20" height="20">&nbsp; Datasets

| **Dataset** | **Size** | **Used for** | **Source** |
| :--- | :--- | :--- | :--- |
| Demo knowledge base | 46 markdown files | CLI demo, first small eval | [`docs/`](docs/) (fictional company) |
| Kubernetes concepts | 182 docs, ~285k words, 300 questions | Chunking experiment | [kubernetes/website](https://github.com/kubernetes/website) `content/en/docs/concepts`, commit `77db41e` |
| PostgreSQL manual | 68 chapters, ~637k words, 300 questions | Chunking replication | [postgres/postgres](https://github.com/postgres/postgres) `doc/src/sgml`, commit `03985e1` |
| BEIR SciFact | 5,183 abstracts, 300 test queries | Retrieval method comparison | [BEIR](https://github.com/beir-cellar/beir) |
| BEIR CQADupStack Android | 22,998 posts, 699 test queries | Retrieval method comparison | [mteb/cqadupstack-android](https://huggingface.co/datasets/mteb/cqadupstack-android) |

The Kubernetes and PostgreSQL questions in [`eval/`](eval/) were written by an LLM agent that could only read the cleaned docs. Each question carries the exact sentence that answers it, and a retrieved chunk counts as a hit when it contains that sentence.

![-----](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## <img src="https://api.iconify.design/lucide/ruler.svg?color=%23E4A700" width="20" height="20">&nbsp; Methodology

1. **Hypothesis first.** Each experiment states its hypothesis in the script docstring before the first run. Follow-ups added after seeing a result say so explicitly.
2. **Blind questions.** Question writers never saw the search engine, the hypothesis or any result.
3. **Paired comparisons.** Methods are compared question by question with an exact two-sided sign test over the questions where they disagree, not by comparing averages.
4. **Uncertainty.** Recall is reported with 95% bootstrap intervals.
5. **Controls.** The chunking experiment includes a fixed-size variant matched to the average section size, to separate "split at headings" from "smaller chunks".

![-----](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## <img src="https://api.iconify.design/lucide/folder-tree.svg?color=%23E4A700" width="20" height="20">&nbsp; Folder Structure

```
.
├── docs/                    demo knowledge base (46 markdown files)
├── eval/                    question sets with expected answers
├── results/                 JSON output of every experiment
├── scripts/
│   ├── run_eval.py          demo knowledge base evaluation
│   ├── beir_eval.py         BM25 / vector / hybrid / rerank on BEIR
│   ├── k8s_prepare.py       clean Kubernetes Hugo markdown
│   ├── pg_prepare.py        convert PostgreSQL DocBook to markdown
│   └── structure_eval.py    chunking experiment (--corpus, --model)
├── src/docsearch/
│   ├── bm25_index.py        BM25 via bm25s
│   ├── vector_index.py      cosine similarity over normalized vectors
│   ├── encoder.py           bge-small and e5-small with their prefixes
│   ├── hybrid.py            Reciprocal Rank Fusion, optional weights
│   ├── structure_variants.py  the five chunking strategies
│   ├── evaluation.py        recall, MRR, bootstrap, sign test
│   └── cli.py               the docsearch and search commands
└── tests/
```

![-----](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## <img src="https://api.iconify.design/lucide/rocket.svg?color=%23E4A700" width="20" height="20">&nbsp; Getting Started

**Requirements:** [uv](https://docs.astral.sh/uv/). PyTorch is installed from the CPU-only wheel index, so no GPU is needed.

```bash
uv sync
uv run docsearch index                                   # chunk docs/, build BM25 + embeddings into .index/
uv run search "timeout 504 nginx" --bm25
uv run search "the page takes forever and then crashes" --vector
uv run search "I can't log in with my token"             # hybrid is the default
uv run pytest
```

Options: `--bm25`, `--vector`, `--hybrid`, `-k 3`.

![-----](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## <img src="https://api.iconify.design/lucide/repeat.svg?color=%23E4A700" width="20" height="20">&nbsp; Reproduce the Experiments

Downloaded sources and embedding caches go to `data/`, which is ignored by git.

**Retrieval methods on BEIR** (downloads the datasets on first run):

```bash
uv run python scripts/beir_eval.py scifact
uv run python scripts/beir_eval.py cqadupstack-android --rerank
```

**Chunking on Kubernetes and PostgreSQL:**

```bash
git clone --depth 1 --filter=blob:none --sparse https://github.com/kubernetes/website.git data/k8s-website
git -C data/k8s-website sparse-checkout set content/en/docs/concepts
git clone --depth 1 --filter=blob:none --sparse https://github.com/postgres/postgres.git data/pg-src
git -C data/pg-src sparse-checkout set doc/src/sgml

uv run python scripts/k8s_prepare.py
uv run python scripts/pg_prepare.py        # needs pandoc

uv run python scripts/structure_eval.py --corpus k8s --model bge
uv run python scripts/structure_eval.py --corpus k8s --model e5
uv run python scripts/structure_eval.py --corpus pg --model bge
uv run python scripts/structure_eval.py --corpus pg --model e5
```

Encoding runs on CPU, so the PostgreSQL runs take the longest (up to about an hour each). Embeddings are cached, so reruns are fast. The docs move over time, so a fresh clone will not match the pinned commits exactly.

![-----](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## <img src="https://api.iconify.design/lucide/triangle-alert.svg?color=%23E4A700" width="20" height="20">&nbsp; Limitations

- Both documentation sets have clean, consistent headings. Documents with poor or missing headings may not benefit.
- The chunking questions were written by an LLM, blind but not by real users, and quotes come from prose, not tables or code.
- Only two small embedding models were tested. Larger models or other rerankers may behave differently.
- The BEIR tasks (claim verification and duplicate questions) differ from typical question answering over internal docs.

![-----](https://raw.githubusercontent.com/andreasbm/readme/master/assets/lines/rainbow.png)

## <img src="https://api.iconify.design/lucide/book-open.svg?color=%23E4A700" width="20" height="20">&nbsp; References

1. Thakur et al. *BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models.* NeurIPS Datasets and Benchmarks, 2021.
2. Cormack, Clarke and Büttcher. *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods.* SIGIR, 2009.
3. Lù. *BM25S: Orders of magnitude faster lexical search via eager sparse scoring.* 2024. [bm25s](https://github.com/xhluca/bm25s)
4. Xiao et al. *C-Pack: Packaged Resources To Advance General Chinese Embedding.* 2023. [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5)
5. Wang et al. *Text Embeddings by Weakly-Supervised Contrastive Pre-training.* 2022. [intfloat/e5-small-v2](https://huggingface.co/intfloat/e5-small-v2)
6. Hoogeveen, Verspoor and Baldwin. *CQADupStack: A Benchmark Data Set for Community Question-Answering Research.* ADCS, 2015.
7. Wadden et al. *Fact or Fiction: Verifying Scientific Claims.* EMNLP, 2020.
