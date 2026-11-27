# Azure Easy Auth + Google JWT Template

Multi-layer authentication pattern for web apps deployed on **Azure Container Apps** with a Google account allowlist.

## Use as a Claude Code plugin

This repository is also a Claude Code plugin. Its skill (`skills/azure-easy-auth-google/SKILL.md`) guides an agent through applying this pattern to another project, using the files here as the reference implementation.

```
/plugin marketplace add SzTk/claude-patterns
/plugin install azure-easy-auth-google@claude-patterns
```

To pick up a new version: `/plugin marketplace update claude-patterns`.

## Architecture

```
[Browser]
    ↓
[Layer 1] Azure Easy Auth       — Redirects unauthenticated users to Google login
    ↓ X-MS-CLIENT-PRINCIPAL-NAME header
[Layer 2] nginx                 — Email allowlist check; non-matching emails → 403
    ↓ Serves frontend
[Layer 3] Frontend (GSI)        — Silent sign-in to obtain a Google ID token
    ↓ Authorization: Bearer <id_token>
[Layer 4] Backend (FastAPI)     — Verifies JWT against Google JWKS independently
```

Layers 1–2 protect the frontend. Layers 3–4 protect the backend API.
The backend does **not** trust Azure; it verifies the Google JWT directly.

## Files

| File | Purpose |
|------|---------|
| `backend/app/core/auth.py` | FastAPI dependency — JWT verification via Google JWKS |
| `backend/app/core/config.py` | Settings: `AUTH_ENABLED`, `GOOGLE_CLIENT_ID`, `ALLOWED_EMAILS` |
| `backend/app/main.py` | Minimal example showing `Depends(require_authorized_user)` |
| `backend/tests/` | Unit tests (no real network calls; Google JWKS is stubbed) |
| `frontend/gsi-auth.js` | GSI silent sign-in — call `getIdToken()` before API requests |
| `frontend/nginx.conf.template` | nginx config with email allowlist and static file serving |
| `deploy/enable-auth.sh` | Azure CLI script to enable Easy Auth on a Container App |

## Quick Start

### 1. Google Cloud Console

1. Go to **APIs & Services → Credentials**
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add authorised redirect URI: `https://<FRONTEND_FQDN>/.auth/login/google/callback`
4. Note the **Client ID** and **Client Secret**

### 2. Backend

Copy `backend/app/core/auth.py` and `backend/app/core/config.py` into your project.

Add the dependency to any endpoint you want to protect:

```python
from app.core.auth import require_authorized_user
from fastapi import Depends

@app.post("/your-endpoint")
async def handler(email = Depends(require_authorized_user)):
    ...
```

Set environment variables in production:

```
AUTH_ENABLED=true
GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
ALLOWED_EMAILS=["you@example.com"]
```

`ALLOWED_EMAILS` must be a JSON array. A comma-separated string fails at startup with a pydantic-settings `SettingsError`.

### 3. Frontend

Add the GSI library tag to your HTML:

```html
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

Copy `frontend/gsi-auth.js`, set `GOOGLE_CLIENT_ID`, then call `getIdToken()` before each API request:

```javascript
const token = await getIdToken();
const resp = await fetch("/your-endpoint", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
});
```

On 401, clear the cache and retry once:

```javascript
if (resp.status === 401) {
    _idToken = null; _tokenExpiry = 0;
    token = await getIdToken();
    resp = await fetch("/your-endpoint", { ... });
}
```

### 4. nginx

Copy `frontend/nginx.conf.template`. Add your allowed email(s) to the `map` block.
Uncomment and adapt the `location /api` proxy block for your API endpoints.

### 5. Deploy Easy Auth

After deploying to Azure Container Apps:

```bash
chmod +x deploy/enable-auth.sh
./deploy/enable-auth.sh <SUBSCRIPTION_ID> <RESOURCE_GROUP> <APP_NAME> <CLIENT_ID> <CLIENT_SECRET>
```

## Local Development

`AUTH_ENABLED` defaults to `false`, so the backend accepts all requests without tokens.
nginx blocks all requests locally (no `X-MS-CLIENT-PRINCIPAL-NAME` header from Easy Auth) — access the backend directly at `http://localhost:8000` instead.

## Running Tests

```bash
cd backend
pip install -e ".[dev]"
pytest tests/ -v
```
