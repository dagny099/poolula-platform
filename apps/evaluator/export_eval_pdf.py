import json
import textwrap
from pathlib import Path

INPUT_PATH = Path(__file__).with_name("poolula_eval_set.jsonl")
OUTPUT_PATH = Path(__file__).with_name("poolula_eval_set.pdf")

PAGE_WIDTH = 600  # 8.5in * 72dpi
PAGE_HEIGHT = 800  # 11in * 72dpi
MARGIN = 38
START_Y = PAGE_HEIGHT - MARGIN
LEADING = 14
MAX_LINES = int((START_Y - MARGIN) / LEADING)


def escape_text(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def wrap_line(text: str, width: int = 95) -> list[str]:
    return textwrap.wrap(text, width=width) or [""]


def build_lines(data: list[dict]) -> list[str]:
    lines: list[str] = [
        "Poolula Evaluation Set",
        "Printable reference for evaluation prompts",
    ]
    for idx, entry in enumerate(data, 1):
        lines.append("")
        lines.extend(wrap_line(f"{idx}. Question: {entry['question']}", 90))
        lines.extend(wrap_line(f"Type: {entry['type']}", 90))
        tools = ", ".join(entry.get("expected_tools", [])) or "—"
        lines.extend(wrap_line(f"Expected tools: {tools}", 90))
        content = ", ".join(entry.get("expected_content", [])) or "—"
        lines.extend(wrap_line(f"Expected content: {content}", 90))
        lines.extend(wrap_line(f"Category: {entry.get('category', 'n/a')}", 90))
    return lines


def chunk_lines(lines: list[str]) -> list[list[str]]:
    pages: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if len(current) >= MAX_LINES:
            pages.append(current)
            current = []
        current.append(line)
    if current:
        pages.append(current)
    return pages


def build_page_stream(lines: list[str]) -> bytes:
    parts = [
        "BT",
        "/F1 12 Tf",
        f"{LEADING} TL",
        f"{MARGIN} {START_Y} Td",
    ]
    for i, line in enumerate(lines):
        if i > 0:
            parts.append("T*")
        parts.append(f"({escape_text(line)}) Tj")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1")


def build_pdf(pages_streams: list[bytes]) -> bytes:
    objects: list[bytes | None] = []

    def add_object(body: bytes | None) -> int:
        objects.append(body)
        return len(objects)

    catalog_ref = add_object(None)  # will point to pages
    pages_ref = add_object(None)  # filled after page refs known
    font_ref = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_refs: list[int] = []
    for stream in pages_streams:
        content_ref = add_object(
            f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
        )
        page_body = (
            f"<< /Type /Page /Parent {pages_ref} 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Contents {content_ref} 0 R /Resources << /Font << /F1 {font_ref} 0 R >> >> >>"
        )
        page_ref = add_object(page_body.encode("latin-1"))
        page_refs.append(page_ref)

    pages_body = f"<< /Type /Pages /Kids [{' '.join(f'{ref} 0 R' for ref in page_refs)}] /Count {len(page_refs)} >>"
    objects[pages_ref - 1] = pages_body.encode("latin-1")
    objects[catalog_ref - 1] = f"<< /Type /Catalog /Pages {pages_ref} 0 R >>".encode("latin-1")

    pdf_parts: list[bytes] = [b"%PDF-1.4\n%\xE2\xE3\xCF\xD3\n"]
    offsets = [0]
    for obj_number, body in enumerate(objects, 1):
        if body is None:
            raise ValueError(f"Object {obj_number} is not defined")
        offset = sum(len(part) for part in pdf_parts)
        offsets.append(offset)
        pdf_parts.append(f"{obj_number} 0 obj\n".encode("latin-1"))
        pdf_parts.append(body)
        pdf_parts.append(b"\nendobj\n")

    xref_start = sum(len(part) for part in pdf_parts)
    pdf_parts.append(f"xref\n0 {len(objects)+1}\n".encode("latin-1"))
    pdf_parts.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf_parts.append(f"{offset:010d} 00000 n \n".encode("latin-1"))

    pdf_parts.append(b"trailer\n")
    pdf_parts.append(f"<< /Size {len(objects)+1} /Root {catalog_ref} 0 R >>\n".encode("latin-1"))
    pdf_parts.append(b"startxref\n")
    pdf_parts.append(f"{xref_start}\n".encode("latin-1"))
    pdf_parts.append(b"%%EOF\n")

    return b"".join(pdf_parts)


def main() -> None:
    data = [json.loads(line) for line in INPUT_PATH.read_text().splitlines() if line.strip()]
    lines = build_lines(data)
    page_chunks = chunk_lines(lines)
    streams = [build_page_stream(chunk) for chunk in page_chunks]
    pdf_bytes = build_pdf(streams)
    OUTPUT_PATH.write_bytes(pdf_bytes)
    print(f"Wrote {OUTPUT_PATH.relative_to(Path.cwd())} with {len(page_chunks)} page(s)")


if __name__ == "__main__":
    main()
