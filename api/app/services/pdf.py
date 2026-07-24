"""PDF extraction, section detection, and chunking."""
import re
from typing import Any

CHUNK_SIZE_CHARS = 3200   # ~800 tokens
CHUNK_OVERLAP_CHARS = 480  # ~120 tokens

_HEADING_RE = re.compile(r"^(\d+(\.\d+)*)\s+\S")
_FIGURE_RE = re.compile(r"^(Figur|Figure|Tabell|Table)\s*\d+", re.IGNORECASE)
_REF_HEADING_RE = re.compile(r"^(Referanser|References|Bibliography|Litteratur)\b", re.IGNORECASE)


def _top_section(path: str | None) -> str:
    if not path:
        return ""
    return path.split(">")[0].strip()


def extract_document(pdf_bytes: bytes) -> dict[str, Any]:
    import fitz  # PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)

    # --- pass 1: collect blocks with page numbers ---
    blocks: list[dict] = []
    current_section: str | None = None
    in_references = False

    for page_num, page in enumerate(doc, start=1):
        for block in page.get_text("blocks"):
            x0, y0, x1, y1, text_raw, block_no, block_type = block
            if block_type != 0:  # skip images
                continue
            text_raw = text_raw.strip()
            if not text_raw:
                continue

            first_line = text_raw.split("\n")[0].strip()

            # Detect reference section
            if _REF_HEADING_RE.match(first_line):
                in_references = True

            # Detect headings by numbered pattern
            m = _HEADING_RE.match(first_line)
            if m:
                num = m.group(1)
                title = first_line[len(num):].strip()
                depth = num.count(".") + 1
                if depth == 1:
                    # top-level section resets the path
                    current_section = f"{num} {title}"
                elif current_section:
                    top = current_section.split(">")[0].strip()
                    current_section = f"{top} > {num} {title}"
                else:
                    current_section = f"{num} {title}"

            kind = "text"
            if _FIGURE_RE.match(first_line):
                kind = "figure_caption"
            elif in_references and not _REF_HEADING_RE.match(first_line):
                kind = "reference"

            blocks.append({
                "text": text_raw,
                "page": page_num,
                "section_path": current_section,
                "kind": kind,
            })

    doc.close()

    full_text = "\n\n".join(b["text"] for b in blocks)
    char_count = len(full_text)

    # --- pass 2: chunk by section boundary + size ---
    chunks: list[dict] = []
    ordinal = 0

    # Group blocks by top-level section
    sections: list[list[dict]] = []
    current_group: list[dict] = []
    current_top = None

    for block in blocks:
        top = _top_section(block["section_path"])
        if top != current_top:
            if current_group:
                sections.append(current_group)
            current_group = [block]
            current_top = top
        else:
            current_group.append(block)
    if current_group:
        sections.append(current_group)

    for section_blocks in sections:
        # Concatenate text for this section, tracking page per char position
        buf = ""
        page_map: list[tuple[int, int]] = []  # (char_start, page)
        section_path = section_blocks[0]["section_path"]
        kind = section_blocks[0]["kind"]

        for block in section_blocks:
            start = len(buf)
            buf += block["text"] + "\n\n"
            page_map.append((start, block["page"]))

        def _page_at(pos: int) -> int:
            pg = section_blocks[0]["page"]
            for char_start, p in page_map:
                if char_start <= pos:
                    pg = p
                else:
                    break
            return pg

        # Slide window
        pos = 0
        while pos < len(buf):
            end = min(pos + CHUNK_SIZE_CHARS, len(buf))
            chunk_text = buf[pos:end].strip()
            if not chunk_text:
                pos = end
                continue

            token_count = max(1, len(chunk_text) // 4)
            page_start = _page_at(pos)
            page_end = _page_at(end - 1)

            chunks.append({
                "ordinal": ordinal,
                "text": chunk_text,
                "page_start": page_start,
                "page_end": page_end,
                "section_path": section_path,
                "kind": kind,
                "token_count": token_count,
            })
            ordinal += 1
            pos = end - CHUNK_OVERLAP_CHARS if end < len(buf) else end

    return {
        "page_count": page_count,
        "char_count": char_count,
        "full_text": full_text,
        "chunks": chunks,
    }
