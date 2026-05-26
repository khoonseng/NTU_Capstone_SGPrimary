# SGPrimary Frontend

Vue 3 frontend for the SGPrimary P1 Ballot Insights and School Recommendation Engine.

Live app: https://test-sg-moe.web.app

## Stack

| Tool | Role |
|---|---|
| Vue 3 | Component framework |
| Vite | Dev server and production build tool |
| Vue Router | Client-side routing |
| PrimeVue | UI component library |
| Tailwind CSS | Utility-first styling |
| Axios | HTTP client for Cloud Run API calls |
| Firebase Hosting | Static hosting and CDN |

## Local Development

Install dependencies and run the Vite dev server:

```bash
cd frontend
npm install
npm run dev
```

The local frontend runs at the URL printed by Vite, usually `http://localhost:5173`.

## Environment Variables

Vite loads environment variables based on the command:

| File | Used by | API target |
|---|---|---|
| `.env.development` | `npm run dev` | `VITE_API_BASE_URL=http://localhost:8000` |
| `.env.production` | `npm run build` | `VITE_API_BASE_URL=https://YOUR_CLOUD_RUN_URL.us-central1.run.app` |

Only variables prefixed with `VITE_` are exposed to browser code. Treat the prefix like a whitelist at build time: without it, Vite keeps the value server-side and `import.meta.env` will not expose it to the frontend.

The shared Axios client reads the value in `src/services/api.js`:

```javascript
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 10000,
})
```

## Production Build

```bash
cd frontend
npm run build
```

This creates `frontend/dist/`, which contains static HTML, CSS, JavaScript, fonts, and assets ready for Firebase Hosting.

To preview the production build locally:

```bash
npm run preview
```

## Firebase Deploy

Firebase Hosting is configured from the repository root in `firebase.json`, with `frontend/dist` as the public directory.

```bash
cd frontend
npm run build
cd ..
firebase deploy
```

Firebase deploys the compiled static app to:

- Primary URL: https://test-sg-moe.web.app
- Secondary URL: https://test-sg-moe.firebaseapp.com

## Smoke Test

After deployment, test on both desktop and mobile:

1. Open https://test-sg-moe.web.app.
2. Navigate from home to recommend.
3. Submit filters and confirm results load.
4. Open the predict panel and confirm the risk assessment loads.
5. Check browser devtools for failed requests or CORS errors.
