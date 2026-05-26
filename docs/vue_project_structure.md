# Frontend Architecture — Vue Project Structure

This document explains the frontend file structure, how the layers connect, and the runtime data flow. Use it as a reference when modifying existing features or adding new ones.

---

## 1. Project File Structure

```mermaid
flowchart TD
    subgraph CONFIG["⚙️ Project Config — steps 1–3"]
        direction LR
        TW["tailwind.config.js\nTells Tailwind which files to scan"]
        CSS["src/style.css\n@tailwind base · components · utilities"]
        ENV[".env.development\n.env.production"]
        MAIN["src/main.js\nRegisters Vue · PrimeVue · Router"]
    end

    subgraph ROUTING["🗺️ Routing and API Service — steps 4–5"]
        direction LR
        ROUTER["router/index.js\n/ → HomeView\n/schools → SchoolsView\n/recommend → RecommendView"]
        API["services/api.js\nAxios instance\nbaseURL from VITE_API_BASE_URL"]
    end

    subgraph VIEWS["🖼️ Views and Components — steps 6–12"]
        direction LR
        APP["App.vue\nNav bar\nrouter-view slot"]
        HOME["views/HomeView.vue\nLanding page\n2 nav buttons"]
        SCHOOLS["views/SchoolsView.vue\nFilter form\nResults grid\nEmpty + error states"]
        CARD["components/SchoolCard.vue\nReusable card\nName · badges · indicators"]
    end

    ENV -->|injects VITE_API_BASE_URL| API
    MAIN -->|registers| ROUTER
    ROUTER -->|renders into router-view| APP
    APP -->|slot for current page| SCHOOLS
    APP -->|slot for current page| HOME
    SCHOOLS -->|renders one per result| CARD
    SCHOOLS -->|calls| API
```

---

## 2. Runtime Data Flow — what happens when a parent clicks Search

```mermaid
sequenceDiagram
    actor Parent
    participant Form as Filter form<br/>(SchoolsView.vue)
    participant Fetch as fetchSchools()<br/>(SchoolsView.vue)
    participant Axios as services/api.js<br/>(Axios instance)
    participant CR as Cloud Run<br/>(FastAPI)
    participant BQ as BigQuery<br/>(dim_school)
    participant Grid as Results grid<br/>(SchoolCard.vue × N)

    Parent->>Form: clicks Search
    Form->>Fetch: triggers fetchSchools()
    Fetch->>Fetch: buildParams() from filter values
    Fetch->>Axios: GET /schools?zone=NORTH&...
    Axios->>CR: HTTP GET with query params
    CR->>BQ: SELECT from dim_school WHERE ...
    BQ-->>CR: rows
    CR-->>Axios: JSON {count, schools:[...]}
    Axios-->>Fetch: response.data
    Fetch->>Grid: schools.value = response.data.schools
    Grid-->>Parent: renders one SchoolCard per result
```

---

## 3. Component Responsibilities

| File | Layer | Responsibility | Modify when... |
|---|---|---|---|
| `tailwind.config.js` | Config | Tells Tailwind which files to scan for class names | Adding a new file type (e.g. `.ts`) |
| `src/style.css` | Config | Loads Tailwind layers, defines reusable CSS utilities (`.badge`, `.filter-select`) | Adding a new reusable CSS class |
| `.env.development` | Config | Sets `VITE_API_BASE_URL` to `localhost:8000` for local dev | Changing the local API port |
| `.env.production` | Config | Sets `VITE_API_BASE_URL` to Cloud Run URL for production builds | Redeploying API to a new Cloud Run URL |
| `src/main.js` | Entry point | Creates the Vue app, registers PrimeVue and Vue Router | Adding a new global plugin or library |
| `router/index.js` | Routing | Maps URL paths to view components | Adding a new page |
| `services/api.js` | API service | Single Axios instance shared across all views | Adding auth headers, changing timeout, adding interceptors |
| `App.vue` | Shell | Permanent nav bar + `<router-view>` slot for page content | Changing the nav bar, adding a footer |
| `views/HomeView.vue` | View | Landing page with navigation buttons | Changing the home page copy or layout |
| `views/SchoolsView.vue` | View | Filter form, API call, results grid, empty/error states | Adding a new filter, changing results layout |
| `views/RecommendView.vue` | View | Recommend page (built in Day 3) | Adding recommend filters or results |
| `components/SchoolCard.vue` | Component | Reusable school card — name, badges, special indicators | Changing how any school card looks across the whole app |

---

## 4. How Vite Selects the API URL

```mermaid
flowchart LR
    DEV["npm run dev\nlocal development"]
    BUILD["npm run build\nproduction build"]
    ENVD[".env.development\nlocalhost:8000"]
    ENVP[".env.production\nCloud Run URL"]
    APIDEV["Axios calls\nlocalhost:8000"]
    APIPROD["Axios calls\nCloud Run"]

    DEV -->|loads| ENVD
    BUILD -->|loads| ENVP
    ENVD --> APIDEV
    ENVP --> APIPROD
```

Vite automatically loads the correct `.env` file based on the command used. No code changes are needed between local development and production — only the build command differs.

---

## 5. Vue Reactivity — why the UI updates automatically

```mermaid
flowchart LR
    API["API returns JSON"]
    REF["schools = ref([])\nreactive variable in SchoolsView"]
    VUE["Vue watches schools\nfor changes"]
    DOM["DOM re-renders\nautomatically"]
    CARDS["SchoolCard × N\nappears on screen"]

    API -->|fetchSchools sets schools.value| REF
    REF -->|change detected| VUE
    VUE --> DOM
    DOM --> CARDS
```

`ref()` and `reactive()` are Vue's reactivity primitives. When `schools.value` is updated after an API response, Vue detects the change and re-renders only the affected part of the DOM — no manual DOM manipulation needed. This is the core value of using Vue over plain JavaScript.

---

*This document covers the frontend structure as of Week 3 Day 2.*
*For the full stack architecture, see [architecture.md](architecture.md).*
