# Replex DTP Service (no cloud AI API)

A document reconstruction + translation pipeline that runs entirely on local,
open-source components — no LLM, no per-request call to any AI API.

## Pipeline

1. **Extraction** — `pdfplumber` reads born-digital PDFs directly (word
   positions, font size, native tables). Scanned PDFs and images fall back to
   local Tesseract OCR via `pytesseract` + `pdf2image`.
2. **Layout reconstruction** — words are clustered into lines and paragraphs
   by position; PDF-native tables (or, for scans, aligned word grids) become
   `TableBlock`s. Reading order is preserved top-to-bottom.
3. **Translation** — [Argos Translate](https://www.argosopentech.com/)
   runs a local neural MT model per language pair. The first request for a
   given pair downloads that pair's model package once (a one-time, cacheable
   file fetch — not a per-call API request); every translation after that is
   fully offline.
4. **.docx generation + validation** — `python-docx` renders paragraphs and
   tables (using `Table Grid` for anything detected as tabular — the same
   technique used to reproduce forms/certificates by hand), then the file is
   reopened to confirm it isn't corrupt before being returned.

## Run locally

Requires system packages `tesseract-ocr` and `poppler-utils` (for `pdftoppm`).

```bash
# Debian/Ubuntu
sudo apt-get install tesseract-ocr poppler-utils

cd service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7860
```

Or with Docker (no system package install needed):

```bash
cd service
docker build -t replex-dtp .
docker run -p 7860:7860 replex-dtp
```

## API

`POST /convert` — multipart form:

| field          | required | description                                  |
|----------------|----------|-----------------------------------------------|
| `file`         | yes      | PDF, PNG, or JPG                              |
| `source_lang`  | no       | ISO 639-1 code of the source text (default `en`) |
| `target_langs` | yes      | comma-separated ISO 639-1 codes, e.g. `fr,de,es` |

Returns a `.docx` for a single target language, or a `.zip` of `.docx` files
for several.

```bash
curl -F "file=@certificate.pdf" -F "source_lang=en" -F "target_langs=fr,de" \
  http://localhost:7860/convert -o output.zip
```

## Deploying for free

**Why not Vercel for this part:** Vercel serverless functions have no
persistent disk for OCR/MT models, a ~50MB deployment size limit, and a
short execution timeout — Tesseract + Argos need real CPU time and hundreds
of MB of models on disk. Use Vercel (or the repo's existing GitHub Pages
workflow) only for the static upload page in `web/`.

**Recommended: Hugging Face Spaces (Docker SDK, free CPU tier)**

1. Create a new Space at huggingface.co/new-space, SDK = **Docker**, visibility = public (free tier).
2. Push the contents of this `service/` directory to the Space's git repo
   (it already contains the `Dockerfile` Spaces will build).
3. The Space builds and serves the container automatically; you get a public
   URL like `https://<your-space>.hf.space`.
4. Point the frontend's `API_BASE` (in `web/index.html`) at that URL.

Alternative: Render.com's free web service tier also works (Docker deploy),
but it sleeps after 15 minutes of inactivity and cold-starts slowly.

## Known limitations

- Output layout is flow-based (top-to-bottom), not pixel-positioned —
  matches the source closely for tables/forms but won't replicate exotic
  multi-column magazine-style layouts.
- Seals, handwritten signatures, and other non-text graphics are not
  reproduced; they're simply omitted rather than approximated.
- Translation quality is standard offline NMT (Argos), not LLM-level
  fluency — acceptable for most forms/certificates but expect rougher
  phrasing on long free-text passages.
