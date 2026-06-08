"""Ingest local text documents and write paragraph-aware chunks to JSONL."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from typing import Iterable, List
from textwrap import shorten

import chromadb
from sentence_transformers import SentenceTransformer


TARGET_CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
OUTPUT_FILE = "chunks.jsonl"
CHROMA_DIRECTORY = "chroma_db"
CHROMA_COLLECTION_NAME = "uic_research_chunks"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


BOILERPLATE_PHRASES = {
    "share",
    "reply",
    "award",
    "upvote",
    "downvote",
    "sort by",
    "log in",
    "sign up",
}


PAGE_ARTIFACT_PATTERNS = [
    re.compile(r"^---\s*page\s*\d+\s*---$", re.IGNORECASE),
    re.compile(r"^\d{1,2}/\d{1,2}/\d{2},\s*\d{1,2}:\d{2}\s*(?:AM|PM).*$", re.IGNORECASE),
    re.compile(r"^r/[A-Za-z0-9_]+(?:\s*[+*]\s*\d+[A-Za-z ]*)?$", re.IGNORECASE),
    re.compile(r"^©\s*Reddit.*$", re.IGNORECASE),
    re.compile(r"^reddit rules.*$", re.IGNORECASE),
    re.compile(r"^privacy policy.*$", re.IGNORECASE),
    re.compile(r"^user agreement.*$", re.IGNORECASE),
    re.compile(r"^your privacy choices.*$", re.IGNORECASE),
    re.compile(r"^accessibility.*$", re.IGNORECASE),
    re.compile(r"^reddit, inc\..*$", re.IGNORECASE),
    re.compile(r"^top posts.*$", re.IGNORECASE),
    re.compile(r"^see more.*$", re.IGNORECASE),
    re.compile(r"^view post in.*$", re.IGNORECASE),
    re.compile(r"^rereddit:.*$", re.IGNORECASE),
]


STOP_BLOCK_PATTERNS = [
    re.compile(r"^top posts.*$", re.IGNORECASE),
    re.compile(r"^see more.*$", re.IGNORECASE),
    re.compile(r"^view post in.*$", re.IGNORECASE),
    re.compile(r"^rereddit:.*$", re.IGNORECASE),
    re.compile(r".*\bupvotes?\s*-\s*\d+\s*comments?\b.*", re.IGNORECASE),
]


LEADING_METADATA_PATTERNS = [
    re.compile(r"^/[A-Za-z0-9_()\-]+\s+", re.IGNORECASE),
    re.compile(r"^(?:search in\s+)?r/[A-Za-z0-9_]+\s+", re.IGNORECASE),
    re.compile(r"^r/[A-Za-z0-9_]+\s*\*\s*.*?ago\s+", re.IGNORECASE),
    re.compile(r"^\+\s*\d+\s*[A-Za-z]{0,3}\s+ago\s+", re.IGNORECASE),
    re.compile(r"^\*\s*\d+\s*[A-Za-z]{0,3}\s+ago\s+", re.IGNORECASE),
    re.compile(r"^[A-Za-z0-9@()_./\-]+\s+@[A-Za-z0-9_()\-]+\s+\+\s*\d+\s*[A-Za-z]{0,3}\s+ago\s+", re.IGNORECASE),
    re.compile(r"^[A-Za-z0-9@()_./\-]+\s+\+\s*\d+\s*[A-Za-z]{0,3}\s+ago\s+", re.IGNORECASE),
    re.compile(r"^[A-Za-z0-9@()_./\-]+\s+[+*]\s*\d+\s*[A-Za-z]{0,3}\s+ago\s+", re.IGNORECASE),
]


HTML_ARTIFACT_PATTERN = re.compile(r"<[^>]+>|&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);")


_EMBEDDING_MODEL: SentenceTransformer | None = None
_CHROMA_COLLECTION = None


def find_documents(root: Path) -> List[Path]:
    """Find all source .txt files in the expected document folders."""

    candidate_dirs = [root / "docs", root / "documents"]
    documents: List[Path] = []

    for candidate_dir in candidate_dirs:
        if candidate_dir.exists() and candidate_dir.is_dir():
            documents.extend(sorted(candidate_dir.glob("*.txt")))

    return documents


def extract_document_body(raw_text: str) -> str:
    """Remove file-level metadata and keep the actual document body when present."""

    marker = "Cleaned content:"
    if marker in raw_text:
        return raw_text.split(marker, 1)[1]
    return raw_text


def is_boilerplate_line(line: str) -> bool:
    """Detect common Reddit/UI noise and obvious metadata lines."""

    normalized = re.sub(r"\s+", " ", line).strip().lower()
    if not normalized:
        return True

    if normalized in BOILERPLATE_PHRASES:
        return True

    if any(pattern.match(line.strip()) for pattern in PAGE_ARTIFACT_PATTERNS):
        return True

    if normalized.startswith(("title:", "source url:", "source type:", "topic:", "cleaned content:")):
        return True

    if normalized.startswith(("start your ", "advertisement", "sponsored", "search in r/")):
        return True

    return False


def strip_leading_metadata(line: str) -> str:
    """Remove Reddit author/time prefixes when they are attached to real content."""

    stripped = line.strip()
    for pattern in LEADING_METADATA_PATTERNS:
        stripped = pattern.sub("", stripped)
    return re.sub(r"\s+", " ", stripped).strip()


def clean_document(text: str) -> str:
    """Strip HTML, unescape entities, remove boilerplate, and normalize whitespace."""

    text = html.unescape(text)
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n").replace("\\t", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_paragraphs: List[str] = []

    for block in re.split(r"\n\s*\n+", text):
        block = block.strip()
        if not block:
            continue

        block_lines = [line.strip() for line in block.splitlines() if line.strip()]
        if block_lines and any(
            pattern.match(line) for line in block_lines for pattern in STOP_BLOCK_PATTERNS
        ):
            break

        kept_lines = []
        for line in block_lines:
            stripped = strip_leading_metadata(line)
            if not stripped or is_boilerplate_line(stripped):
                continue
            kept_lines.append(stripped)

        paragraph = re.sub(r"\s+", " ", " ".join(kept_lines)).strip()
        if paragraph:
            cleaned_paragraphs.append(paragraph)

    return "\n\n".join(cleaned_paragraphs)


def split_into_paragraphs(text: str) -> List[str]:
    """Split cleaned text into paragraph units while dropping empty entries."""

    return [paragraph.strip() for paragraph in re.split(r"\n\s*\n+", text) if paragraph.strip()]


def build_base_chunks(paragraphs: Iterable[str], target_size: int) -> List[str]:
    """Greedily accumulate paragraphs into chunks close to the target size."""

    chunks: List[str] = []
    current_parts: List[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph_length = len(paragraph)
        separator_length = 2 if current_parts else 0
        prospective_length = current_length + separator_length + paragraph_length

        if current_parts and prospective_length > target_size:
            chunk_text = "\n\n".join(current_parts).strip()
            if chunk_text:
                chunks.append(chunk_text)
            current_parts = [paragraph]
            current_length = paragraph_length
            continue

        current_parts.append(paragraph)
        current_length = prospective_length

    if current_parts:
        chunk_text = "\n\n".join(current_parts).strip()
        if chunk_text:
            chunks.append(chunk_text)

    return chunks


def apply_overlap(chunks: List[str], overlap_size: int) -> List[str]:
    """Add a character overlap from the end of each chunk to the start of the next."""

    if not chunks:
        return []

    overlapped_chunks = [chunks[0].strip()]
    for chunk in chunks[1:]:
        prefix = overlapped_chunks[-1][-overlap_size:].strip()
        combined = chunk.strip()
        if prefix:
            combined = f"{prefix}\n\n{combined}"
        if combined:
            overlapped_chunks.append(combined)

    return overlapped_chunks


def chunk_document(text: str, target_size: int, overlap_size: int) -> List[str]:
    """Chunk a single document using paragraph-aware chunking with overlap."""

    cleaned_text = clean_document(extract_document_body(text))
    if not cleaned_text:
        return []

    paragraphs = split_into_paragraphs(cleaned_text)
    base_chunks = build_base_chunks(paragraphs, target_size)
    return apply_overlap(base_chunks, overlap_size)


def warn_on_html_artifacts(chunks: List[dict]) -> None:
    """Warn when any chunk still contains obvious HTML-like artifacts."""

    suspicious = [chunk for chunk in chunks if HTML_ARTIFACT_PATTERN.search(chunk["text"])]
    if suspicious:
        print(
            f"Warning: {len(suspicious)} chunk(s) still contain HTML-like artifacts.",
            file=sys.stderr,
        )


def write_chunks(chunks: List[dict], output_path: Path) -> None:
    """Write chunk records to a JSONL file, one object per line."""

    with output_path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk, ensure_ascii=False) + "\n")


def load_chunks_jsonl(chunks_path: Path) -> List[dict]:
    """Load chunk records from the JSONL file created by the ingestion step."""

    if not chunks_path.exists():
        return []

    records: List[dict] = []
    with chunks_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def get_embedding_model() -> SentenceTransformer:
    """Load the sentence-transformers model once and reuse it for embeddings."""

    global _EMBEDDING_MODEL

    if _EMBEDDING_MODEL is None:
        _EMBEDDING_MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _EMBEDDING_MODEL


def build_chroma_collection(root: Path, chunk_records: List[dict]):
    """Embed chunk texts and store them in a persistent ChromaDB collection."""

    client = chromadb.PersistentClient(path=str(root / CHROMA_DIRECTORY))
    try:
        client.delete_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=CHROMA_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    model = get_embedding_model()
    texts = [chunk["text"] for chunk in chunk_records]
    embeddings = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

    collection.add(
        ids=[chunk["chunk_id"] for chunk in chunk_records],
        documents=texts,
        metadatas=[
            {
                "source": chunk["source"],
                "source_path": chunk["source_path"],
                "chunk_id": chunk["chunk_id"],
            }
            for chunk in chunk_records
        ],
        embeddings=embeddings.tolist(),
    )

    return collection


def retrieve(query: str, k: int = 5) -> List[dict]:
    """Run semantic search over the ChromaDB collection and return ranked matches."""

    if _CHROMA_COLLECTION is None:
        raise RuntimeError("ChromaDB collection has not been initialized yet.")

    model = get_embedding_model()
    query_embedding = model.encode([query], normalize_embeddings=True, convert_to_numpy=True)
    result = _CHROMA_COLLECTION.query(
        query_embeddings=query_embedding.tolist(),
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    retrieved: List[dict] = []
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for document, metadata, distance in zip(documents, metadatas, distances):
        similarity = 1.0 - float(distance) if distance is not None else 0.0
        retrieved.append(
            {
                "text": document,
                "metadata": metadata,
                "similarity": similarity,
            }
        )

    return retrieved


def print_retrieval_results(query: str, results: List[dict]) -> None:
    """Print retrieved chunks and similarity scores for a single test query."""

    print(f"\nQuery: {query}")
    if not results:
        print("No matches returned.")
        return

    for index, result in enumerate(results, start=1):
        source = result["metadata"].get("source", "unknown")
        similarity = result["similarity"]
        text = result["text"].strip()
        preview = shorten(re.sub(r"\s+", " ", text), width=600, placeholder="...")
        print(f"[{index}] {source} | similarity={similarity:.4f}")
        print(preview)
        print()


def main() -> int:
    """Run the ingestion pipeline and print a short validation summary."""

    root = Path(__file__).resolve().parent
    documents = find_documents(root)

    if not documents:
        print("Warning: no .txt documents were found in docs/ or documents/.", file=sys.stderr)

    all_chunks: List[dict] = []
    chunk_counter = 1

    for document_path in documents:
        raw_text = document_path.read_text(encoding="utf-8", errors="ignore")
        document_chunks = chunk_document(raw_text, TARGET_CHUNK_SIZE, CHUNK_OVERLAP)

        for text in document_chunks:
            all_chunks.append(
                {
                    "chunk_id": f"chunk_{chunk_counter:05d}",
                    "source": document_path.name,
                    "source_path": str(document_path.resolve()),
                    "text": text,
                }
            )
            chunk_counter += 1

    output_path = root / OUTPUT_FILE
    write_chunks(all_chunks, output_path)

    chunk_records = load_chunks_jsonl(output_path)
    if not chunk_records:
        print("Warning: chunks.jsonl did not contain any chunks.", file=sys.stderr)
        return 0

    global _CHROMA_COLLECTION
    _CHROMA_COLLECTION = build_chroma_collection(root, chunk_records)

    print(f"Documents loaded: {len(documents)}")
    print(f"Total chunks: {len(all_chunks)}")

    for chunk in all_chunks[:5]:
        preview = re.sub(r"\s+", " ", chunk["text"]).strip()
        if len(preview) > 160:
            preview = preview[:157] + "..."
        print(f"- {chunk['source']}: {preview}")

    if len(all_chunks) < 50:
        print(f"Warning: total chunks are fewer than 50 ({len(all_chunks)}).", file=sys.stderr)

    warn_on_html_artifacts(all_chunks)

    test_queries = [
        "How do students recommend getting involved in undergraduate research?",
        "What is EVL?",
        "What research areas are available in the AI Lab?",
    ]

    for query in test_queries:
        results = retrieve(query, k=5)
        print_retrieval_results(query, results)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())