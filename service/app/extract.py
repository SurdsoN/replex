"""Extract text and layout metadata from a source document.

Born-digital PDFs are read directly with pdfplumber (byte-accurate word
positions and native table grids). Scanned PDFs and images fall back to
local Tesseract OCR. Neither path calls out to a cloud AI service.
"""
from __future__ import annotations

import io

import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image

from .schemas import ExtractedDocument, Line, Page, ParagraphBlock, TableBlock, Word

# Pages with less extractable text than this are treated as scans and sent to OCR.
MIN_DIGITAL_CHARS_PER_PAGE = 20


def extract_document(file_bytes: bytes, filename: str) -> ExtractedDocument:
    if filename.lower().endswith(".pdf"):
        return _extract_pdf(file_bytes)
    return _extract_image(file_bytes)


def _extract_pdf(file_bytes: bytes) -> ExtractedDocument:
    pages: list[Page] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            if len(page.extract_text() or "") >= MIN_DIGITAL_CHARS_PER_PAGE:
                pages.append(_page_from_pdfplumber(page))
            else:
                image = convert_from_bytes(
                    file_bytes, first_page=page_index + 1, last_page=page_index + 1, dpi=300
                )[0]
                pages.append(_page_from_ocr(image, float(page.width), float(page.height)))
    return ExtractedDocument(pages=pages)


def _extract_image(file_bytes: bytes) -> ExtractedDocument:
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    page = _page_from_ocr(image, float(image.width), float(image.height))
    return ExtractedDocument(pages=[page])


def _page_from_pdfplumber(page) -> Page:
    words = [
        Word(text=w["text"], x0=w["x0"], x1=w["x1"], top=w["top"], bottom=w["bottom"],
             size=float(w.get("height") or 11.0))
        for w in page.extract_words(use_text_flow=True, keep_blank_chars=False)
    ]
    tables = _tables_from_pdfplumber(page)
    table_bboxes = [t.bbox for t in tables]
    remaining = [w for w in words if not _inside_any(w, table_bboxes)]
    paragraphs = _words_to_paragraphs(remaining)
    return Page(width=float(page.width), height=float(page.height), paragraphs=paragraphs, tables=tables)


def _tables_from_pdfplumber(page) -> list[TableBlock]:
    tables = []
    for t in page.find_tables():
        rows = t.extract()
        tables.append(
            TableBlock(
                bbox=(t.bbox[0], t.bbox[1], t.bbox[2], t.bbox[3]),
                rows=[[(cell or "").strip() for cell in row] for row in rows],
            )
        )
    return tables


def _inside_any(word: Word, bboxes) -> bool:
    for (x0, top, x1, bottom) in bboxes:
        if word.x0 >= x0 - 1 and word.x1 <= x1 + 1 and word.top >= top - 1 and word.bottom <= bottom + 1:
            return True
    return False


def _page_from_ocr(image: Image.Image, width_pt: float, height_pt: float) -> Page:
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    scale_x = width_pt / image.width
    scale_y = height_pt / image.height
    words: list[Word] = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        if not text or int(data["conf"][i]) < 0:
            continue
        x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
        words.append(Word(
            text=text,
            x0=x * scale_x, x1=(x + w) * scale_x,
            top=y * scale_y, bottom=(y + h) * scale_y,
            size=h * scale_y,
        ))
    return Page(width=width_pt, height=height_pt, paragraphs=_words_to_paragraphs(words), tables=[])


def _words_to_paragraphs(words: list[Word]) -> list[ParagraphBlock]:
    if not words:
        return []
    ordered = sorted(words, key=lambda w: (round(w.top / 3), w.x0))

    lines: list[Line] = []
    current = [ordered[0]]
    for w in ordered[1:]:
        prev = current[-1]
        if abs(w.top - prev.top) <= max(prev.size, w.size) * 0.6:
            current.append(w)
        else:
            lines.append(_line_from_words(current))
            current = [w]
    lines.append(_line_from_words(current))

    paragraphs: list[ParagraphBlock] = []
    para_lines = [lines[0]]
    for line in lines[1:]:
        prev = para_lines[-1]
        if line.top - prev.bottom <= prev.size * 0.9:
            para_lines.append(line)
        else:
            paragraphs.append(_paragraph_from_lines(para_lines))
            para_lines = [line]
    paragraphs.append(_paragraph_from_lines(para_lines))
    return paragraphs


def _line_from_words(words: list[Word]) -> Line:
    ordered = sorted(words, key=lambda w: w.x0)
    return Line(
        text=" ".join(w.text for w in ordered),
        x0=min(w.x0 for w in ordered), x1=max(w.x1 for w in ordered),
        top=min(w.top for w in ordered), bottom=max(w.bottom for w in ordered),
        size=sum(w.size for w in ordered) / len(ordered),
    )


def _paragraph_from_lines(lines: list[Line]) -> ParagraphBlock:
    return ParagraphBlock(
        text="\n".join(l.text for l in lines),
        bbox=(min(l.x0 for l in lines), min(l.top for l in lines),
              max(l.x1 for l in lines), max(l.bottom for l in lines)),
        size=sum(l.size for l in lines) / len(lines),
    )
