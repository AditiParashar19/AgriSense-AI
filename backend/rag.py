"""
rag.py
------
Retrieval-Augmented Generation (RAG) engine for the AgriSense-AI chatbot.

Builds a FAISS vector store from agriculture knowledge base files stored
inside backend/data/ (.pdf AND .txt), using local HuggingFace sentence
embeddings (no API key or network call required for embeddings). The
resulting index is cached to disk so it only needs to be rebuilt when
the source files change.

Improvements over the previous version:
    - Loads BOTH .pdf and .txt files from backend/data/ (previously .pdf only).
    - Smaller, more overlapping chunks for more precise retrieval.
    - MMR (Maximal Marginal Relevance) retrieval by default, which reduces
      redundant/near-duplicate chunks and improves answer diversity.
    - Removed an unused GOOGLE_API_KEY check that no longer applies now
      that embeddings run locally via HuggingFace.
"""

import glob
import hashlib
import json
import os
from typing import List, Optional

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
VECTORSTORE_DIR = os.path.join(BASE_DIR, "data", "faiss_index")
MANIFEST_PATH = os.path.join(VECTORSTORE_DIR, "manifest.json")

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Module-level caches so the model and vector store are only loaded/built
# once per process (this is the main cost of "faster retrieval").
_embeddings: Optional[HuggingFaceEmbeddings] = None
_vectorstore: Optional[FAISS] = None


def _get_embeddings() -> HuggingFaceEmbeddings:
    """
    Instantiate (once) the local HuggingFace sentence-embedding model.
    Runs entirely locally - no API key required.
    """
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    return _embeddings


def _current_source_files() -> List[str]:
    """All .pdf and .txt files currently in backend/data/, sorted for a stable fingerprint."""
    os.makedirs(DATA_DIR, exist_ok=True)
    files = glob.glob(os.path.join(DATA_DIR, "*.pdf")) + glob.glob(os.path.join(DATA_DIR, "*.txt"))
    return sorted(files)


def _compute_fingerprint(files: List[str]) -> str:
    """
    Compute a fingerprint of the knowledge base directory based on each
    file's name, size, and last-modified time. Any added, removed, or
    edited file changes this fingerprint, which is what lets
    build_vectorstore() detect a stale cached index automatically.
    """
    hasher = hashlib.sha256()
    for path in files:
        stat = os.stat(path)
        hasher.update(os.path.basename(path).encode("utf-8"))
        hasher.update(str(stat.st_size).encode("utf-8"))
        hasher.update(str(int(stat.st_mtime)).encode("utf-8"))
    return hasher.hexdigest()


def _read_stored_fingerprint() -> Optional[str]:
    if not os.path.exists(MANIFEST_PATH):
        return None
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f).get("fingerprint")
    except Exception:
        return None


def _write_manifest(fingerprint: str, files: List[str]) -> None:
    os.makedirs(VECTORSTORE_DIR, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"fingerprint": fingerprint, "files": [os.path.basename(p) for p in files]},
            f, indent=2,
        )


def _load_knowledge_base_documents() -> List[Document]:
    """
    Load and split every .pdf and .txt file found in backend/data/ into
    text chunks suitable for embedding.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    pdf_paths = glob.glob(os.path.join(DATA_DIR, "*.pdf"))
    txt_paths = glob.glob(os.path.join(DATA_DIR, "*.txt"))

    if not pdf_paths and not txt_paths:
        raise RuntimeError(
            f"No agriculture knowledge base files found in '{DATA_DIR}'. "
            "Please add reference .pdf or .txt files (soil health, fertilizers, "
            "irrigation, crop diseases, pest management, etc.) before using the chatbot."
        )

    all_docs: List[Document] = []

    for pdf_path in pdf_paths:
        all_docs.extend(PyPDFLoader(pdf_path).load())

    for txt_path in txt_paths:
        all_docs.extend(TextLoader(txt_path, encoding="utf-8").load())

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(all_docs)

    # Drop near-empty chunks (e.g. stray whitespace/page breaks) that add
    # noise to the vector store without adding retrieval value.
    return [c for c in chunks if len(c.page_content.strip()) > 40]


def build_vectorstore(force_rebuild: bool = False) -> FAISS:
    """
    Build (or load from disk cache) the FAISS vector store over all
    knowledge base files in backend/data/.

    Automatically rebuilds whenever the contents of backend/data/ have
    changed since the index was last built (a file was added, removed,
    or edited) - so adding a new PDF just requires restarting the
    backend, not manually deleting the faiss_index folder.
    """
    global _vectorstore

    current_files = _current_source_files()
    current_fingerprint = _compute_fingerprint(current_files)
    stored_fingerprint = _read_stored_fingerprint()
    is_stale = current_fingerprint != stored_fingerprint

    if _vectorstore is not None and not force_rebuild and not is_stale:
        return _vectorstore

    embeddings = _get_embeddings()

    index_file = os.path.join(VECTORSTORE_DIR, "index.faiss")
    if os.path.exists(index_file) and not force_rebuild and not is_stale:
        _vectorstore = FAISS.load_local(
            VECTORSTORE_DIR, embeddings, allow_dangerous_deserialization=True
        )
        return _vectorstore

    chunks = _load_knowledge_base_documents()
    _vectorstore = FAISS.from_documents(chunks, embeddings)

    os.makedirs(VECTORSTORE_DIR, exist_ok=True)
    _vectorstore.save_local(VECTORSTORE_DIR)
    _write_manifest(current_fingerprint, current_files)

    return _vectorstore


def retrieve_relevant_chunks(query: str, k: int = 5, fetch_k: int = 15) -> List[Document]:
    """
    Retrieve the top-k most relevant, diverse document chunks for a
    query using Maximal Marginal Relevance (MMR) search. MMR first
    fetches `fetch_k` candidates by similarity, then re-ranks them to
    balance relevance against redundancy - this avoids returning 4-5
    near-duplicate chunks from the same paragraph.
    """
    vectorstore = build_vectorstore()
    return vectorstore.max_marginal_relevance_search(query, k=k, fetch_k=fetch_k)


def format_context(chunks: List[Document]) -> str:
    """
    Format retrieved document chunks into a single context string,
    including source file names for traceability / citations.
    """
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        source = os.path.basename(chunk.metadata.get("source", "unknown"))
        parts.append(f"[Source {i}: {source}]\n{chunk.page_content.strip()}")
    return "\n\n".join(parts)


def list_sources(chunks: List[Document]) -> List[str]:
    """Return the unique, human-readable source file names used in a set of chunks."""
    seen = []
    for chunk in chunks:
        source = os.path.basename(chunk.metadata.get("source", "unknown"))
        if source not in seen:
            seen.append(source)
    return seen