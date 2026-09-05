# Replex DTP — Frontend

A static upload page for the [Replex DTP service](../service/README.md).
No build step — plain HTML/JS.

## Configure the backend URL

Edit `API_BASE` in `index.html`, or set it at runtime by injecting a small
script before `index.html`'s own script tag:

```html
<script>window.REPLEX_API_BASE = "https://your-space.hf.space";</script>
```

## Deploy to Vercel

```bash
npm i -g vercel   # one-time
cd web
vercel --prod
```

Or via the Vercel dashboard: "Add New Project" → import this repo → set the
project's **Root Directory** to `web` → deploy. No framework preset needed
(it's static HTML).
