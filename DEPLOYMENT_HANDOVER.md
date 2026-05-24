# Deployment Handover — sigma-research → Cloud Run

Read this only when working on the sigma-research backend deployment.

## Status
**sigma-research FastAPI backend — NOT yet deployed. Blocked.** (sigma-quant frontend is already live on Cloudflare Pages — unaffected.)

## The blocker
Cloud **Build** is blocked by a Google Cloud **org policy**. Do **not** try to route the deploy through Cloud Build.

**Path forward: use Cloud Run's native GitHub integration** (build-and-deploy-from-repo), which sidesteps Cloud Build entirely. Repo: `smz3/sigma-research`.

## Rules when helping with this
- **Prefer `gcloud` CLI** over console-click instructions.
- **Never guess at org policies or service-account configs** — ask Syafiq to paste the exact error log, then diagnose from it.
- Avoid Cloud Build; use Cloud Run native GitHub integration.

## Next steps (when unblocked)
1. Connect `smz3/sigma-research` to Cloud Run via native GitHub integration.
2. Confirm the service account has Cloud Run deploy permissions (not Cloud Build).
3. Set env/secrets (Qdrant, Groq, FRED keys) as Cloud Run service config — never in the repo.
4. Deploy, smoke-test the FastAPI health endpoint, then point sigma-quant at the live URL.
