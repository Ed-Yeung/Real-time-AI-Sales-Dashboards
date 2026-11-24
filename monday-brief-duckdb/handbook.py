from pathlib import Path
import re

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from pypdf import PdfReader

from config import get_llm

HANDBOOK_DIR = Path(__file__).parent / "data" / "handbooks"
TOP_K = 5
CHUNK = 800

_CACHE = {"key": None, "chunks": [], "vectors": None, "model": None}


class HandbookMatch(BaseModel):
    needs_definition: bool = Field(description="True if the question needs a calculation that is not a raw column")
    found: bool
    kind: str = Field(description="metric, explore, document, or none")
    name: str = ""
    formula: str = ""
    quote: str = ""
    source: str = ""
    page: int = 0
    conflict: bool = False
    conflict_note: str = ""


def list_handbooks() -> list[Path]:
    if not HANDBOOK_DIR.exists():
        return []
    return sorted(HANDBOOK_DIR.glob("*.pdf"))


def save_handbook(name: str, raw: bytes) -> Path:
    HANDBOOK_DIR.mkdir(parents=True, exist_ok=True)
    safe = Path(name).name
    if not safe.lower().endswith(".pdf"):
        safe += ".pdf"
    path = HANDBOOK_DIR / safe
    path.write_bytes(raw)
    return path


def _chunks() -> list[dict]:
    items = []
    for path in list_handbooks():
        reader = PdfReader(str(path))
        for index, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            start = 0
            while start < len(text):
                piece = text[start:start + CHUNK].strip()
                if piece:
                    items.append({"source": path.name, "page": index, "text": piece})
                start += CHUNK - 100
    return items


def _cache_key() -> tuple:
    return tuple((path.name, path.stat().st_mtime) for path in list_handbooks())


def _embedder():
    if _CACHE["model"] is None:
        from fastembed import TextEmbedding
        _CACHE["model"] = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _CACHE["model"]


def _index() -> tuple[list[dict], np.ndarray]:
    key = _cache_key()
    if _CACHE["key"] == key and _CACHE["vectors"] is not None:
        return _CACHE["chunks"], _CACHE["vectors"]
    chunks = _chunks()
    if not chunks:
        _CACHE.update(key=key, chunks=[], vectors=np.zeros((0, 1)))
        return [], _CACHE["vectors"]
    vectors = np.array(list(_embedder().embed([item["text"] for item in chunks])))
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / np.clip(norms, 1e-9, None)
    _CACHE.update(key=key, chunks=chunks, vectors=vectors)
    return chunks, vectors


def retrieve(question: str, k: int = TOP_K) -> list[dict]:
    chunks, vectors = _index()
    if not chunks:
        return []
    query = np.array(list(_embedder().embed([question])))
    query = query / np.clip(np.linalg.norm(query), 1e-9, None)
    scores = vectors @ query[0]
    order = np.argsort(scores)[::-1][:k]
    picked = []
    for index in order:
        item = dict(chunks[int(index)])
        item["score"] = float(scores[int(index)])
        picked.append(item)
    return picked


def handbook_text(question: str = "") -> str:
    picked = retrieve(question) if question else []
    if not picked:
        return ""
    return "\n\n".join(
        f"[file {item['source']}] [page {item['page']}]\n{item['text']}"
        for item in picked
    )


def _quote_ok(quote: str, text: str) -> bool:
    if not quote.strip():
        return False
    folded = re.sub(r"\s+", " ", text).lower()
    needle = re.sub(r"\s+", " ", quote).lower()
    return needle in folded


def _ask(question: str, text: str, retry: bool = False) -> dict:
    extra = ""
    if retry:
        extra = " The previous quote was not an exact sentence from the passages. Copy one sentence exactly."
    system = (
        "You match one English question to the handbook passages below. "
        "Raw columns are sales, cost, units, orders. "
        "If the question only compares, ranks, or asks why using those columns, "
        "set kind to explore, needs_definition false, found false. "
        "If it needs a calculation that is not a raw column, set needs_definition true and kind metric. "
        "Set found true only when a passage defines it. Copy the formula and the defining sentence exactly. "
        "Set source to the file name and page to the page number from the markers. "
        "If two files define the same metric with different formulas, set conflict true, found false, "
        "and put both file names and formulas in conflict_note. Never average formulas. Never invent a formula. "
        "If it only asks what a handbook says, set kind document and copy one sentence exactly with source and page."
        + extra
    )
    result = get_llm(0).with_structured_output(HandbookMatch).invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=f"Question: {question}\n\nPassages:\n{text}"),
        ]
    )
    return result.model_dump()


def match_handbook(question: str) -> dict:
    empty = {
        "needs_definition": False,
        "found": False,
        "kind": "explore",
        "name": "",
        "formula": "",
        "quote": "",
        "source": "",
        "page": 0,
        "conflict": False,
        "conflict_note": "",
    }
    text = handbook_text(question)
    if not text.strip():
        return empty
    data = _ask(question, text)
    if data.get("conflict"):
        data["found"] = False
        data["formula"] = ""
        return data
    if (data.get("found") or data.get("kind") == "document") and not _quote_ok(data.get("quote") or "", text):
        data = _ask(question, text, retry=True)
        if data.get("conflict"):
            data["found"] = False
            data["formula"] = ""
            return data
        if not _quote_ok(data.get("quote") or "", text):
            data["found"] = False
            if data.get("kind") == "document":
                data["quote"] = ""
    return data
