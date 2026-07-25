# Deploy the backend as a separate Vercel container

This deployment keeps the existing Vercel frontend project unchanged and creates
a second Vercel project for the FastAPI backend.

## What the container includes

- The FastAPI backend
- The persistent Chroma index
- The Markdown legal-document templates
- A CPU-only PyTorch installation
- A build-time copy of `intfloat/e5-base-v2`

The source PDFs, ingestion scripts, tests, frontend, local virtual environment,
and secret `.env` file are excluded from the container.

## 1. Push the repository

Commit and push the files in this repository. In particular, ensure these files
are present in Git:

- `Dockerfile.vercel`
- `.dockerignore`
- `backend/requirements.vercel.txt`
- `vector_dbs/chroma/**`
- `knowledge_base/templates/**`

Never commit `.env`.

## 2. Create the backend project

1. Open the [Vercel dashboard](https://vercel.com/dashboard).
2. Select **Add New > Project**.
3. Import the same Git repository used by the frontend.
4. Give it a distinct name, such as `jurigpt-api`.
5. Leave **Root Directory** as the repository root (`./`). The Dockerfile needs
   access to `backend`, `vector_dbs`, and `knowledge_base/templates`.
6. If Vercel asks for a framework preset, select **Other**.
7. Do not set custom Build or Output Directory commands. Vercel detects
   `Dockerfile.vercel`.

## 3. Add backend environment variables

In the new backend project, open **Settings > Environment Variables** and add:

```text
GEMINI_API_KEY
GEMINI_MODEL
TEMPERATURE
MAX_OUTPUT_TOKENS
TIMEOUT
MONGODB_URI
MONGODB_DATABASE
JWT_SECRET_KEY
JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
CORS_ORIGINS
VERCEL_SUPPORT_LARGE_FUNCTIONS
```

Use the same values as the working Render backend. Set:

```text
CORS_ORIGINS=https://YOUR-FRONTEND.vercel.app
VERCEL_SUPPORT_LARGE_FUNCTIONS=1
```

`CORS_ORIGINS` accepts multiple comma-separated origins if a custom frontend
domain must also be allowed. Do not add a trailing slash to an origin.

Do not add `E5_MODEL_NAME` on Vercel. The Docker image sets it to the baked
model directory automatically.

## 4. Configure the function

In **Settings > Functions**:

1. Confirm Fluid Compute is enabled.
2. Set the maximum duration to **300 seconds**.
3. Keep the Hobby **Standard** instance (2 GB RAM and 1 vCPU).
4. Choose the region closest to the MongoDB Atlas cluster. If the database is
   also near India and there is no better-known match, use Mumbai (`bom1`).

Vercel container functions do not provide a fixed outbound IP. MongoDB Atlas
must allow connections from Vercel's dynamic addresses. For a short-lived demo,
this commonly means allowing `0.0.0.0/0` in Atlas Network Access while retaining
a strong database username and password.

## 5. Deploy and verify the backend

Start the deployment. The first build will be relatively slow because it
downloads CPU PyTorch and the E5 model into the image.

After Vercel reports a successful deployment, open:

```text
https://YOUR-BACKEND.vercel.app/health
```

Expected response:

```json
{"status":"healthy"}
```

Then open:

```text
https://YOUR-BACKEND.vercel.app/docs
```

## 6. Point the frontend at the new backend

Open the existing frontend Vercel project and change:

```text
VITE_API_BASE_URL=https://YOUR-BACKEND.vercel.app
```

Do not include a trailing slash. Redeploy the frontend after saving the value.

Register or sign in, submit a question, and watch the backend project's runtime
logs during the first request. The container streams response metadata before
Gemini begins producing answer tokens.

## Optional local container verification

Start Docker Desktop and make sure its Linux engine is running, then execute:

```powershell
docker build -f Dockerfile.vercel -t jurigpt-vercel-backend:test .
docker run --rm -p 8000:8000 --env-file .env -e PORT=8000 jurigpt-vercel-backend:test
```

In another terminal:

```powershell
Invoke-RestMethod http://localhost:8000/health
```
