# SGPrimary — Architecture Documentation

This document covers two architecture perspectives:

1. [Full Stack Architecture](#1-full-stack-architecture) — how all components fit together end-to-end
2. [Firebase Hosting — How the Vue App is Served](#2-firebase-hosting--how-the-vue-app-is-served) — the deploy and runtime journey in detail

---

## 1. Full Stack Architecture

This diagram shows the complete system — from your WSL development machine through to a parent's browser.

```mermaid
flowchart TD
    subgraph DEV["💻 WSL Ubuntu — Development Machine"]
        direction TB
        NVM["nvm\nNode version manager"]
        NODE["Node.js + npm\nJS runtime · package manager"]
        NVM -->|installs| NODE

        subgraph FRONTEND["frontend/ — Vue Project"]
            direction LR
            VITE["Vite\nbuild toolchain"]
            VUE["Vue 3\ncomponent framework"]
            TW["Tailwind CSS\nutility styling"]
            PV["PrimeVue\nUI component library"]
            VR["Vue Router\nclient-side routing"]
            AX["Axios\nHTTP client"]
        end

        NODE -->|powers| FRONTEND
    end

    subgraph BUILD["🔨 Build Step — npm run build"]
        DIST["frontend/dist/\nplain HTML · CSS · JS"]
    end

    subgraph DEPLOY["🚀 Deploy Step — firebase deploy"]
        FBCLI["Firebase CLI\nreads dist/ and uploads"]
    end

    FRONTEND -->|compiles to| DIST
    DIST -->|uploaded by| FBCLI

    subgraph GCP["☁️ Google Cloud Platform — test-sg-moe"]
        direction TB

        subgraph HOSTING["Firebase Hosting"]
            CDN["CDN Edge Nodes\n~150 cities worldwide\ntest-sg-moe.web.app"]
        end

        subgraph BACKEND["Cloud Run"]
            API["FastAPI\n/health · /schools\n/recommend · /predict"]
        end

        subgraph DWH["BigQuery"]
            MART["mart_school_analysis\ndim_school\nfact_balloting"]
        end

        API -->|queries| MART
    end

    FBCLI -->|pushes files to| CDN

    subgraph BROWSER["📱 Parent's Browser — Singapore"]
        direction TB
        LOAD["1. Download Vue app\nfrom nearest CDN node"]
        RUN["2. Vue app runs\nVue Router shows page"]
        CALL["3. Axios calls\nCloud Run API"]
        RENDER["4. Vue renders\nresults for parent"]

        LOAD --> RUN --> CALL --> RENDER
    end

    CDN -->|"serves HTML · CSS · JS"| LOAD
    CALL -->|"GET /recommend?zone=NORTH"| API
    API -->|"returns JSON"| CALL
```

### Component Reference

| Component | Layer | Role |
|---|---|---|
| nvm | Dev machine | Installs and manages Node.js versions — like pyenv for Python |
| Node.js + npm | Dev machine | JS runtime and package manager — required to run Vite and install packages |
| Vite | Build toolchain | Dev server (`npm run dev`) and compiler (`npm run build`) — converts `.vue` files to plain HTML/CSS/JS |
| Vue 3 | Frontend framework | Component framework — lets you write reusable UI pieces as `.vue` files |
| Tailwind CSS | Styling | Utility-first CSS — style via class names (`text-red-500`, `p-4`) instead of writing CSS |
| PrimeVue | UI components | Pre-built dropdowns, tables, cards, badges — saves building from scratch |
| Vue Router | Navigation | Client-side routing between `/schools`, `/recommend` — no server roundtrip per page |
| Axios | HTTP client | Makes API calls to Cloud Run — sends requests, receives JSON responses |
| Firebase CLI | Deploy tool | Uploads `frontend/dist/` to Firebase Hosting via `firebase deploy` |
| Firebase Hosting | CDN | Serves static files to browsers worldwide — no server computation |
| Cloud Run | Backend | Runs FastAPI, computes responses, queries BigQuery on each API call |
| BigQuery | Data warehouse | Stores `mart_school_analysis`, `dim_school`, `fact_balloting` — source of truth |

---

## 2. Firebase Hosting — How the Vue App is Served

This diagram zooms into Firebase Hosting specifically — showing what happens at deploy time and at runtime.

```mermaid
flowchart LR
    subgraph DEPLOYTIME["🔨 Deploy Time — runs once per change"]
        direction LR
        SRC["Vue source files\n.vue · .js · .css"]
        BUILD["npm run build\nVite compiles"]
        DIST2["frontend/dist/\nHTML · CSS · JS only"]
        ORIGIN["Firebase origin server\nGoogle's storage"]
        EDGES["CDN edge nodes\n~150 cities worldwide"]

        SRC -->|Vite strips .vue syntax| BUILD
        BUILD --> DIST2
        DIST2 -->|firebase deploy| ORIGIN
        ORIGIN -->|replicates to| EDGES
    end

    subgraph RUNTIME["⚡ Runtime — every time a parent opens the app"]
        direction TB

        subgraph STEP1["Step 1 — fetch the app"]
            direction LR
            PARENT["Parent's browser\nSingapore"]
            SGNODE["Nearest CDN node\ne.g. Singapore"]
            PARENT -->|"requests test-sg-moe.web.app"| SGNODE
            SGNODE -->|"returns HTML · CSS · JS instantly"| PARENT
        end

        subgraph STEP2["Step 2 — run the app"]
            direction LR
            VUERUN["Vue app runs in browser\nVue Router shows correct page"]
        end

        subgraph STEP3["Step 3 — fetch data"]
            direction LR
            AXIOSREQ["Axios sends API call\nGET /recommend?zone=NORTH"]
            CR["Cloud Run\nFastAPI + BigQuery"]
            AXIOSRESP["Axios receives JSON\nVue renders results"]
            AXIOSREQ -->|CORS checked here| CR
            CR -->|JSON response| AXIOSRESP
        end

        STEP1 --> STEP2 --> STEP3
    end
```

### Key Insight — Two Different Roles

| | Firebase Hosting | Cloud Run |
|---|---|---|
| **Analogy** | Bookshelf — books already printed, just handed out | Kitchen — every order cooked fresh on demand |
| **What it serves** | Static files — same HTML/CSS/JS for every visitor | Dynamic responses — different JSON per API call |
| **Computation** | None — pure file delivery | Yes — Python code runs, BigQuery queried |
| **When it runs** | Immediately, from nearest CDN node | On each API request, 50–200ms response time |
| **Cost** | Free tier — 10GB storage, 360MB/day transfer | Billed per request and compute time |
| **Do they talk to each other?** | No — the parent's browser connects them | No — Cloud Run never calls Firebase |

> **Important:** Firebase Hosting and Cloud Run never communicate directly.
> The parent's browser is the only bridge between the two — it downloads
> the Vue app from Firebase, then makes API calls directly to Cloud Run.

---

*This document was created as part of the SGPrimary capstone project.*
*Author: Khoon Seng*
