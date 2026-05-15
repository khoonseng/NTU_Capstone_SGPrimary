# Setup Guide for API local development and Cloud Run deployment

## (1) Running the API locally

### Prerequisites

- conda environment `sgprimary` activated
- `.env` file configured at repo root
- GCP service account JSON key in `keys/` folder

### Start the API server

```bash
# Activate conda environment
conda activate sgprimary

# From repo root
uvicorn api.main:app --reload
```

The `--reload` flag enables hot-reloading — the server restarts automatically when code changes are detected. Remove it in production.

The API will be available at:
- **Swagger UI (interactive docs):** `http://127.0.0.1:8000/docs`
- **Health check:** `http://127.0.0.1:8000/health`

### Smoke test locally

```bash
# Health check
curl http://127.0.0.1:8000/health

# Schools endpoint
curl "http://127.0.0.1:8000/schools?zone_code=NORTH"

# Recommend endpoint
curl "http://127.0.0.1:8000/recommend?zone_code=NORTH&phase=2C"

# Predict endpoint
curl "http://127.0.0.1:8000/predict?school_name=ADMIRALTY%20PRIMARY%20SCHOOL&phase=2C"
```

---

## (2) Building and pushing the Docker image

### Prerequisites

- Docker Desktop installed with WSL 2 integration enabled
- `gcloud` CLI installed and authenticated (`gcloud auth login`)
- GCP project set (`gcloud config set project YOUR_GCP_PROJECT_ID`)
- Artifact Registry repository created (one-time setup — see below)

### One-time: Create Artifact Registry repository

```bash
gcloud artifacts repositories create sgprimary \
  --repository-format=docker \
  --location=us-central1 \
  --description="SGPrimary API Docker images"
```

### One-time: Authenticate Docker to Artifact Registry

```bash
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### Build the image

Run from repo root — not from inside `api/`:

```bash
docker build -f api/Dockerfile -t sgprimary-api:local .
```

### Tag for Artifact Registry

```bash
docker tag sgprimary-api:local \
  us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/sgprimary/sgprimary-api:latest
```

Replace `YOUR_GCP_PROJECT_ID` with your GCP project ID.

### Push to Artifact Registry

```bash
docker push us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/sgprimary/sgprimary-api:latest
```

### Test the container locally before pushing

```bash
docker run --rm -p 8080:8080 \
  --env-file .env \
  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/key.json \
  -v $(pwd)/keys/YOUR_KEY_FILE.json:/tmp/key.json:ro \
  sgprimary-api:local
```

Replace `YOUR_KEY_FILE.json` with your service account key filename. Then verify:

```bash
curl http://localhost:8080/health
```

---

## (5) Deploying to Cloud Run

### Prerequisites

- Docker image pushed to Artifact Registry
- Service account with `roles/bigquery.admin` and `roles/storage.admin`
- Cloud Run API enabled in GCP project

### First-time deployment

```bash
gcloud run deploy sgprimary-api \
  --image us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/sgprimary/sgprimary-api:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --service-account YOUR_SERVICE_ACCOUNT@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars GCP_PROJECT_ID=YOUR_GCP_PROJECT_ID \
  --memory 512Mi \
  --timeout 60
```

Replace:
- `YOUR_GCP_PROJECT_ID` — your GCP project ID
- `YOUR_SERVICE_ACCOUNT` — your service account name e.g. `backend-service-account`

When prompted to enable the Cloud Run API, answer `Y`.

On success you will see:
```bash
Service [sgprimary-api] revision [sgprimary-api-00001-xxx] has been deployed
and is serving 100 percent of traffic.
Service URL: https://YOUR_CLOUD_RUN_URL.us-central1.run.app
```

Save the Service URL — this is your public API endpoint.

### Redeploying after code changes

Any Python code change requires a full rebuild and redeploy:

```bash
# 1. Rebuild
docker build -f api/Dockerfile -t sgprimary-api:local .

# 2. Tag
docker tag sgprimary-api:local \
  us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/sgprimary/sgprimary-api:latest

# 3. Push
docker push us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/sgprimary/sgprimary-api:latest

# 4. Deploy
gcloud run deploy sgprimary-api \
  --image us-central1-docker.pkg.dev/YOUR_GCP_PROJECT_ID/sgprimary/sgprimary-api:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --service-account YOUR_SERVICE_ACCOUNT@YOUR_GCP_PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars GCP_PROJECT_ID=YOUR_GCP_PROJECT_ID \
  --memory 512Mi \
  --timeout 60
```

### Verify the deployed API

```bash
# Health check
curl https://YOUR_CLOUD_RUN_URL.us-central1.run.app/health

# View live logs
gcloud run services logs read sgprimary-api --region us-central1
```

### Rolling back to a previous revision

```bash
# List available revisions
gcloud run revisions list --service sgprimary-api --region us-central1

# Roll back to a specific revision
gcloud run services update-traffic sgprimary-api \
  --to-revisions REVISION_NAME=100 \
  --region us-central1
```

### Postman collection

A Postman collection is available at `api/postman/SGPrimary_API.postman_collection.json`.

To use it:
1. Import the collection into Postman desktop app
2. Create a Postman environment with variable `base_url` set to your Cloud Run URL or `http://localhost:8000` for local dev
3. Activate the environment before sending requests

