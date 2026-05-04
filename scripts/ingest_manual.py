#!/usr/bin/env python
"""
产品手册向量摄取脚本 — 支持 Markdown 和 PDF

读取 data/product_manual.md + data/pdfs/*.pdf → 分块 → 生成 BGE 语义向量 → 存入本地向量存储

用法:
    cd O:\AII\RAG
    .\.venv\Scripts\python.exe scripts\ingest_manual.py
"""
import os
import sys
import re
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DEMO_MODE"] = "true"


def load_markdown(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_pdf(path: str) -> str:
    """Extract text from PDF using pdfplumber."""
    import pdfplumber
    with pdfplumber.open(path) as pdf:
        pages = []
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)


def load_all_documents(data_dir: str) -> list[dict]:
    """Load all documents: markdown + PDFs. Returns list of {filename, text}."""
    docs = []

    # Load markdown manual
    md_path = os.path.join(data_dir, "product_manual.md")
    if os.path.exists(md_path):
        docs.append({"filename": "product_manual.md", "text": load_markdown(md_path)})

    # Load PDFs
    pdf_dir = os.path.join(data_dir, "pdfs")
    if os.path.exists(pdf_dir):
        for fname in sorted(os.listdir(pdf_dir)):
            if fname.endswith(".pdf"):
                fpath = os.path.join(pdf_dir, fname)
                try:
                    text = load_pdf(fpath)
                    docs.append({"filename": fname, "text": text})
                    print(f"  Loaded PDF: {fname} ({len(text)} chars)")
                except Exception as e:
                    print(f"  SKIP {fname}: {e}")

    return docs


def chunk_text(text: str, source: str, max_chars: int = 300) -> list:
    """Chunk text by headings or paragraph boundaries."""
    chunks = []

    # Try ## heading split first
    sections = re.split(r'\n(?=## )', text)
    if len(sections) == 1:
        # No markdown headings — split by double newline (paragraphs), then merge short ones
        paragraphs = text.split("\n\n")
        current = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current) + len(para) < max_chars:
                current += para + "\n\n"
            else:
                if current.strip():
                    chunks.append({"title": "", "content": current.strip(), "source": source})
                current = para + "\n\n"
        if current.strip():
            chunks.append({"title": "", "content": current.strip(), "source": source})
        return chunks

    for section in sections:
        section = section.strip()
        if not section:
            continue

        title_match = re.match(r'##\s+(.+)', section)
        title = title_match.group(1).strip() if title_match else ""

        if len(section) > max_chars:
            paragraphs = section.split("\n\n")
            current = ""
            for para in paragraphs:
                if len(current) + len(para) < max_chars:
                    current += para + "\n\n"
                else:
                    if current.strip():
                        chunks.append({"title": title, "content": current.strip(), "source": source})
                    current = para + "\n\n"
            if current.strip():
                chunks.append({"title": title, "content": current.strip(), "source": source})
        else:
            chunks.append({"title": title, "content": section, "source": source})

    return chunks


def classify_chunk(content: str) -> str:
    """Classify chunk type by keyword analysis."""
    content_lower = content.lower()
    specs = ["spec", "parameter", "rated", "voltage", "current", "power", "dimension", "weight",
             "accuracy", "range", "resolution", "output", "规格", "参数", "功率", "电压", "电流", "尺寸", "重量"]
    faults = ["fault", "error", "alarm", "troubleshoot", "solution", "check", "replace",
              "故障", "排查", "报警", "解决", "症状"]
    compat = ["compatib", "interchangeable", "replacement", "alternate",
              "兼容", "替换", "配套"]
    install = ["install", "mount", "wiring", "connect", "接地", "安装", "接线", "连接"]

    score = {"spec": 0, "troubleshoot": 0, "compatibility": 0, "general": 0}

    for kw in specs:
        if kw in content_lower:
            score["spec"] += 1
    for kw in faults:
        if kw in content_lower:
            score["troubleshoot"] += 1
    for kw in compat:
        if kw in content_lower:
            score["compatibility"] += 1
    for kw in install:
        if kw in content_lower:
            score["general"] += 1

    best = max(score, key=score.get)
    return best if score[best] > 0 else "general"


def main():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

    print("=" * 60)
    print("Loading documents...")
    docs = load_all_documents(data_dir)
    print(f"Total documents: {len(docs)}")

    # Chunk all documents
    all_chunks = []
    for doc in docs:
        chunks = chunk_text(doc["text"], doc["filename"])
        for c in chunks:
            c["chunk_type"] = classify_chunk(c["content"])
        all_chunks.extend(chunks)
        print(f"  {doc['filename']}: {len(chunks)} chunks")

    print(f"\nTotal chunks: {len(all_chunks)}")

    # Show chunk type distribution
    from collections import Counter
    type_counts = Counter(c["chunk_type"] for c in all_chunks)
    print(f"Chunk types: {dict(type_counts)}")

    # Generate BGE embeddings
    from src.embeddings.bge_embedder import get_encoder
    encoder = get_encoder()
    contents = [c["content"] for c in all_chunks]

    print(f"\nGenerating BGE embeddings for {len(contents)} chunks (dim={encoder.dimension})...")
    vectors_list = encoder.encode(contents)

    # Check if we got real embeddings or hash fallback
    # Hash fallback vectors are deterministic — check a few for non-trivially-zero values
    sample_vec = vectors_list[0]
    non_zero = sum(1 for v in sample_vec if abs(v) > 0.01)
    is_real_embedding = non_zero > 10
    print(f"Embedding type: {'BGE semantic (real)' if is_real_embedding else 'Hash fallback (degraded)'}")
    print(f"  Sample: dim={len(sample_vec)}, non-zero elements={non_zero}")

    # Save to local vector store
    import numpy as np
    vectors = np.array(vectors_list, dtype=np.float32)
    metadata = []
    for i, chunk in enumerate(all_chunks):
        metadata.append({
            "chunk_id": i,
            "chunk_type": chunk["chunk_type"],
            "section_title": chunk["title"],
            "content": chunk["content"],
            "source": chunk["source"],
        })

    from src.storage.local_vector_store import get_local_vector_store
    store = get_local_vector_store()
    store.save(vectors, metadata)

    print(f"\nDone. {len(vectors)} vectors saved to data/local_vectors.npz")
    print(f"Vector store: available={store.is_available}, count={store.count}")


if __name__ == "__main__":
    main()
