"""Render translated structured pages into a .docx file.

python-docx is flow-based rather than pixel-positioned, so absolute layout is
approximated by reading order (top-to-bottom) plus nested tables for anything
that was detected as a table grid - the same trick manual DTP reconstruction
uses for forms, certificates, and contracts.
"""
from __future__ import annotations

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

from .schemas import ExtractedDocument, ParagraphBlock, TableBlock

_HEADING_SIZE_THRESHOLD = 16.0
_MIN_FONT_PT = 6.0
_MAX_FONT_PT = 48.0


def build_docx(document: ExtractedDocument, output_path: str) -> None:
    doc = Document()
    for page_index, page in enumerate(document.pages):
        if page_index > 0:
            doc.add_page_break()
        for kind, block in _ordered_blocks(page):
            if kind == "paragraph":
                _add_paragraph(doc, block)
            else:
                _add_table(doc, block)
    doc.save(output_path)


def _ordered_blocks(page):
    blocks = [("paragraph", p) for p in page.paragraphs] + [("table", t) for t in page.tables]
    blocks.sort(key=lambda item: item[1].bbox[1])
    return blocks


def _add_paragraph(doc: Document, block: ParagraphBlock) -> None:
    text = block.translated_text if block.translated_text is not None else block.text
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    run.font.size = Pt(max(_MIN_FONT_PT, min(block.size, _MAX_FONT_PT)))
    run.font.bold = block.size >= _HEADING_SIZE_THRESHOLD
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT


def _add_table(doc: Document, block: TableBlock) -> None:
    rows = block.translated_rows if block.translated_rows is not None else block.rows
    if not rows or not rows[0]:
        return
    n_cols = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=n_cols)
    table.style = "Table Grid"
    for r, row in enumerate(rows):
        for c in range(n_cols):
            table.cell(r, c).text = row[c] if c < len(row) else ""
