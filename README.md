# Replex

- `index.html.html` — marketing/landing page for the Claude-based "Replex" DTP
  document translation skill (deployed via GitHub Pages, see
  `.github/workflows/static.yml`).
- `service/` — a separate, standalone DTP reconstruction + translation
  pipeline that uses **no cloud AI API**: local OCR (Tesseract) + rule-based
  layout reconstruction + offline neural machine translation (Argos
  Translate) + `.docx` generation via python-docx. See
  [`service/README.md`](service/README.md) for architecture, local setup,
  and free deployment instructions (Hugging Face Spaces).
- `web/` — a minimal static upload page for the service above, deployable to
  Vercel. See [`web/README.md`](web/README.md).
