# MedConnect Explorer — RAG System

Build a Retrieval-Augmented Generation system with two pipelines: **Ingestion** (process 50 Wikipedia medical articles into ChromaDB) and **Inference** (answer user questions using semantic search + LLM).

## User Review Required

> [!IMPORTANT]
> This requires an **OpenAI API key** set as `OPENAI_API_KEY` in a `.env` file for both embeddings (`text-embedding-3-small`) and generation (`gpt-4o-mini`).

> [!WARNING]
> New dependencies will be added: `chromadb`, `openai`, `tiktoken`, `langchain-text-splitters`.

---

## Proposed Changes

### Configuration

#### [MODIFY] [requirements.txt](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/requirements.txt)
Add: `chromadb`, `openai`, `tiktoken`, `langchain-text-splitters`

#### [MODIFY] [config.py](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/src/utils/config.py)
Add `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `LLM_MODEL`, `CHROMA_PERSIST_DIR`, chunking params (`CHUNK_SIZE`, `CHUNK_OVERLAP`)

---

### Ingestion Pipeline — `src/ingestion/`

#### [NEW] [fetcher.py](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/src/ingestion/fetcher.py)
- Reuses logic from `find_medical_articles_simple.py` to fetch 50 articles
- Returns list of dicts: `{title, url, text, categories}`

#### [NEW] [cleaner.py](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/src/ingestion/cleaner.py)
- Regex to strip `[1]`, `[14]`-style citations
- Remove "References", "Further Reading", "External Links" sections
- Normalize whitespace, strip hidden Unicode

#### [NEW] [chunker.py](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/src/ingestion/chunker.py)
- `RecursiveCharacterTextSplitter` with `tiktoken` (`cl100k_base`) tokenizer
- Chunk size: 800 tokens, overlap: 80 tokens
- Each chunk gets metadata: `article_title`, `url`, `category`, `chunk_index`

#### [NEW] [embedder.py](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/src/ingestion/embedder.py)
- OpenAI `text-embedding-3-small` embedding
- Batch embedding with rate-limit handling

#### [NEW] [pipeline.py](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/src/ingestion/pipeline.py)
- Orchestrator: fetch → clean → chunk → embed → store in ChromaDB
- Single entry point: `run_ingestion()`

---

### Inference Pipeline — `src/inference/`

#### [NEW] [search.py](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/src/inference/search.py)
- Embed user query with same model
- ChromaDB similarity search (top 5 chunks)
- Optional metadata filtering via `where` clause

#### [NEW] [prompt_builder.py](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/src/inference/prompt_builder.py)
- Build "Mega-Prompt" with system prompt, retrieved context chunks, and user question
- Include article titles for citation

#### [NEW] [pipeline.py](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/src/inference/pipeline.py)
- Orchestrator: embed query → search → build prompt → call LLM → return answer
- Single entry point: `query(question)`

---

### Entry Point

#### [NEW] [main.py](file:///Users/xalandames/Documents/Senior-Project-Group-2/wikipedia-api-poc/src/main.py)
- CLI with two commands:
  - `python src/main.py ingest` — runs the ingestion pipeline
  - `python src/main.py query "your question"` — runs the inference pipeline

---

## Verification Plan

### Automated Tests
1. Run `python src/main.py ingest` — verify ChromaDB collection is created with chunks
2. Run `python src/main.py query "What are the symptoms of diabetes?"` — verify grounded answer with citations
3. Verify chunk count and metadata in ChromaDB
