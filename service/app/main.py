"""Replex DTP service.

A document-reconstruction and translation pipeline with no cloud AI API in
the loop: local OCR (Tesseract) + rule-based layout reconstruction + offline
neural machine translation (Argos Translate) + python-docx rendering.
"""
from __future__ import annotations

import copy
import io
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .docx_builder import build_docx
from .extract import extract_document
from .schemas import ExtractedDocument
from .translate_engine import translate_text
from .validate import validate_docx

app = FastAPI(title="Replex DTP Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/convert")
async def convert(
    file: UploadFile = File(...),
    source_lang: str = Form("en"),
    target_langs: str = Form(...),
) -> StreamingResponse:
    """Reconstruct the uploaded document and translate it into one or more languages.

    target_langs is a comma-separated list of ISO 639-1 codes, e.g. "fr,de,es".
    Returns a single .docx for one target language, or a .zip of .docx files for several.
    """
    languages = [code.strip() for code in target_langs.split(",") if code.strip()]
    if not languages:
        raise HTTPException(400, "At least one target language is required")

    file_bytes = await file.read()
    try:
        extracted = extract_document(file_bytes, file.filename or "upload.pdf")
    except Exception as exc:
        raise HTTPException(422, f"Could not read document: {exc}") from exc

    stem = Path(file.filename or "document").stem
    results: list[tuple[str, bytes]] = []
    with TemporaryDirectory() as tmp_dir:
        for lang in languages:
            translated = _translate_document(extracted, source_lang, lang)
            out_path = Path(tmp_dir) / f"{stem}.{lang}.docx"
            try:
                build_docx(translated, str(out_path))
                validate_docx(str(out_path))
            except Exception as exc:
                raise HTTPException(500, f"Failed generating {lang} document: {exc}") from exc
            results.append((out_path.name, out_path.read_bytes()))

    if len(results) == 1:
        name, data = results[0]
        return StreamingResponse(
            io.BytesIO(data),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{name}"'},
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in results:
            zf.writestr(name, data)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=translations.zip"},
    )


def _translate_document(extracted: ExtractedDocument, source_lang: str, target_lang: str) -> ExtractedDocument:
    doc = copy.deepcopy(extracted)
    for page in doc.pages:
        for paragraph in page.paragraphs:
            paragraph.translated_text = translate_text(paragraph.text, source_lang, target_lang)
        for table in page.tables:
            table.translated_rows = [
                [translate_text(cell, source_lang, target_lang) for cell in row] for row in table.rows
            ]
    return doc
