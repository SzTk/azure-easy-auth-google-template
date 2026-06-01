# CLAUDE.md

This repository is a **reusable template** for the Azure Easy Auth + Google JWT multi-layer authentication pattern.

## What this template provides

A 4-layer authentication stack for Azure Container Apps:

1. **Azure Easy Auth** — forces Google login; unauthenticated users are redirected
2. **nginx email allowlist** — checks `X-MS-CLIENT-PRINCIPAL-NAME` header; blocks non-allowed emails with 403
3. **Frontend GSI silent sign-in** — obtains a Google ID token without user interaction
4. **Backend JWT verification** — validates the token directly against Google JWKS (RS256, audience, issuer, email_verified, allowed_emails)

## Key files

- `backend/app/core/auth.py` — `require_authorized_user` FastAPI dependency (copy as-is)
- `backend/app/core/config.py` — `AUTH_ENABLED`, `GOOGLE_CLIENT_ID`, `ALLOWED_EMAILS` settings (copy as-is)
- `frontend/gsi-auth.js` — `getIdToken()` function; set `GOOGLE_CLIENT_ID` at the top
- `frontend/nginx.conf.template` — add allowed emails to the `map` block
- `deploy/enable-auth.sh` — Azure CLI script; all parameters passed as arguments

## How to apply this pattern to a new project

1. Copy `backend/app/core/auth.py` and `config.py` into the new project's `app/core/`
2. Add `Depends(require_authorized_user)` to protected FastAPI endpoints
3. Copy `frontend/gsi-auth.js`; replace `GOOGLE_CLIENT_ID` placeholder
4. Copy `frontend/nginx.conf.template`; add allowed emails; add proxy location blocks for API endpoints
5. Copy `deploy/enable-auth.sh`
6. Set `AUTH_ENABLED=true`, `GOOGLE_CLIENT_ID`, `ALLOWED_EMAILS` as production env vars

## Important constraints

- `GOOGLE_CLIENT_ID` must be the **same value** in `gsi-auth.js` (frontend) and as the `GOOGLE_CLIENT_ID` env var on the backend
- `allowed_emails` controls access at **both** the nginx layer (map block) and the backend layer; keep them in sync
- The backend verifies JWTs **independently of Azure** — it calls Google JWKS directly
- `AUTH_ENABLED=false` (default) disables all backend auth checks; safe for local dev and tests
- nginx blocks all traffic locally without Easy Auth — test the backend directly at port 8000
