"""
RAG ingest CLI.

Usage:
    python -m app.rag.ingest --path docs/
"""
import argparse
import asyncio
import hashlib
import re
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from app.settings import settings


def parse_frontmatter(text: str) -> tuple[dict, str]:
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = frontmatter_pattern.match(text)
    if not match:
        return {"product_area": "general"}, text
    fm_text = match.group(1)
    content = text[match.end():]
    metadata = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip()
    return metadata, content


def chunk_markdown(text: str, max_tokens: int = 400) -> list[tuple[str, str]]:
    metadata, content = parse_frontmatter(text)
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+?)\s*$', re.MULTILINE)
    matches = list(heading_pattern.finditer(content))
    if not matches:
        return [(content, "")]
    chunks = []
    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section = content[start:end].strip()
        if not section:
            continue
        if len(section) // 4 <= max_tokens:
            chunks.append((section, heading))
        else:
            paragraphs = section.split('\n\n')
            current = ""
            for para in paragraphs:
                if not para.strip():
                    continue
                test = current + "\n\n" + para if current else para
                if len(test) // 4 > max_tokens and current:
                    chunks.append((current, heading))
                    current = para
                else:
                    current = test
            if current:
                chunks.append((current, heading))
    return chunks


def generate_chunk_id(file_path: str, heading: str, chunk_index: int) -> str:
    raw = f"{file_path}::{heading}::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def ingest_directory(docs_path: Path, chunk_size: int) -> None:
    ef = DefaultEmbeddingFunction()
    chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    try:
        collection = chroma_client.get_collection("helix_docs", embedding_function=ef)
    except Exception:
        collection = chroma_client.create_collection("helix_docs", embedding_function=ef)

    md_files = list(docs_path.rglob("*.md"))
    print(f"Found {len(md_files)} markdown files in {docs_path}")
    total_chunks = 0

    for file_path in md_files:
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"  Error reading {file_path.name}: {e}")
            continue

        metadata, _ = parse_frontmatter(text)
        product_area = metadata.get("product_area", "general")
        title = metadata.get("title", file_path.stem)
        chunks = chunk_markdown(text, max_tokens=chunk_size)
        if not chunks:
            continue

        print(f"  {file_path.name}: {len(chunks)} chunks")
        ids, metadatas, documents = [], [], []

        for chunk_index, (chunk_text, heading) in enumerate(chunks):
            if not chunk_text.strip():
                continue
            chunk_id = generate_chunk_id(str(file_path), heading, chunk_index)
            ids.append(chunk_id)
            metadatas.append({
                "chunk_id": chunk_id,
                "source_file": str(file_path),
                "product_area": product_area,
                "title": title,
                "heading": heading,
                "chunk_index": chunk_index,
            })
            documents.append(chunk_text[:8000])

        if not ids:
            continue

        try:
            collection.upsert(ids=ids, metadatas=metadatas, documents=documents)
            total_chunks += len(ids)
        except Exception as e:
            print(f"    Upsert error: {e}")

    print(f"Ingest complete. Total chunks: {total_chunks}")
    print(f"Collection now has {collection.count()} chunks")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--chunk-size", type=int, default=400)
    args = parser.parse_args()
    asyncio.run(ingest_directory(args.path, args.chunk_size))


if __name__ == "__main__":
    main()