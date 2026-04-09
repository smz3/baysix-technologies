# Sigma-Research Cloud Run Deployment — Handover

**Status:** Stuck at Cloud Build logging configuration  
**Date:** 2026-04-07  
**Next Owner:** Claude or Gemini  

---

## What We're Trying to Do

Deploy the sigma-research FastAPI backend (semantic search API) to Google Cloud Run so the **Vector Context panel** works in the production frontend at `syafiqmzin-sigma-quant.pages.dev`.

Currently the panel shows "Vector DB offline" because the backend only runs locally.

---

## What's Done

✅ **Code fixes** — all committed to smz3/sigma-research:
- `pipelines/server.py` — PORT env var, CORS with Cloudflare Pages URL
- `pipelines/store/qdrant_store.py` — API key support, deterministic ID generation
- `src/app/api/intelligence/search/route.ts` — runtime='nodejs'
- `Dockerfile` — Python 3.11-slim, uvicorn on port 8080

✅ **Data pipeline** — 245 documents indexed in Qdrant Cloud (sigma_market collection)

✅ **Infrastructure** — Qdrant Cloud cluster created and populated

✅ **Repository structure** — sigma-research is clean separate GitHub repo (deleted monorepo symlink)

---

## What's Blocked

**Google Cloud organization policy issue:**

When trying to trigger Cloud Build, it fails with:
```
Failed to trigger build: if 'build.service_account' is specified, the build must either 
(a) specify 'build.logs_bucket', (b) use REGIONAL_USER_OWNED_BUCKET, or 
(c) use CLOUD_LOGGING_ONLY / NONE logging options: invalid argument
```

The Cloud Build UI doesn't expose these logging configuration options, so we can't proceed via the standard Cloud Build → Cloud Run path.

---

## Next Steps (In Order)

### **Step 1: Check if Image Was Built**
```bash
# Go to: https://console.cloud.google.com/artifacts/docker
# Check if sigma-research image exists in Artifact Registry
# If YES → Go to Step 2
# If NO → Go to Step 3
```

### **Step 2: Deploy Existing Image (If Built)**
1. Go to **Cloud Run** → **CREATE SERVICE**
2. Choose **"Deploy one revisions from an image repository"**
3. Click image selector → find `sigma-research` in Artifact Registry
4. Set Service name: `sigma-research-api`
5. Region: `us-east4`
6. Authentication: `Allow unauthenticated invocations`
7. Click **"Show advanced settings"** → **Runtime environment variables:**
   - `QDRANT_URL` = 
   - `QDRANT_API_KEY` = 
8. Click **CREATE**
9. Wait ~2 minutes for deployment
10. Copy the Cloud Run URL (format: `https://sigma-research-api-xxxxx-us-east4.a.run.app`)
11. Go to **Step 4**

### **Step 3: Deploy from GitHub (If No Image)**
1. Go to **Cloud Run** → **CREATE SERVICE**
2. Choose **"Deploy from a GitHub repository"** (native integration, no Cloud Build)
3. Select: `smz3/sigma-research`, branch `master`
4. Dockerfile path: `/Dockerfile`
5. Service name: `sigma-research-api`
6. Region: `us-east4`
7. Set environment variables (QDRANT_URL, QDRANT_API_KEY) — same as Step 2
8. Click **CREATE**
9. Wait ~3-5 minutes
10. Copy Cloud Run URL
11. Go to **Step 4**

### **Step 4: Update Cloudflare Pages (Final Step)**
1. Go to **Cloudflare Pages** → `sigma-quant` → **Settings** → **Environment variables** → **Production**
2. Click **Add variable**
   - Name: `SIGMA_RESEARCH_URL`
   - Value: (paste Cloud Run URL from Step 2 or 3)
3. Click **Save**
4. Go to **Deployments** → Click **Trigger Deployment** on the latest deployment
5. Wait for redeploy (~1-2 minutes)

### **Step 5: Test It**
Visit: `https://syafiqmzin-sigma-quant.pages.dev/intelligence`

Vector Context panel should now show semantic search results instead of "Vector DB offline".

---

## Key Files & Credentials

**Repo:** `https://github.com/smz3/sigma-research`

**Environment Variables (.env):**
```
QDRANT_URL=
QDRANT_API_KEY=

**Qdrant Cloud:**
- Collection: `sigma_market`
- Documents indexed: 245
- Status: Live and verified working

---

## Troubleshooting

**If Cloud Run deployment fails:**
- Check build logs in Cloud Build (History tab)
- Verify QDRANT_URL and QDRANT_API_KEY are correct
- Ensure Qdrant Cloud cluster is still accessible

**If Vector Context still shows offline:**
- Verify SIGMA_RESEARCH_URL is set in Cloudflare Pages
- Check that Cloudflare deployment was triggered
- Test Cloud Run health: `GET https://your-cloud-run-url/health`

---

## Why This Approach Works

✅ Avoids Cloud Build logging policy issue entirely  
✅ Uses Cloud Run's native GitHub integration (simpler)  
✅ All code is production-ready (already tested locally)  
✅ Qdrant Cloud is stable and verified  

---

**Good luck! You're very close.** 🚀
