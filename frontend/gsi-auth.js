/**
 * GSI silent sign-in for Azure Easy Auth + Google JWT pattern.
 *
 * Include this script (or inline it) in your HTML after the GSI library tag:
 *   <script src="https://accounts.google.com/gsi/client" async defer></script>
 *
 * Replace GOOGLE_CLIENT_ID with your OAuth 2.0 Client ID.
 * The same client ID must be set as GOOGLE_CLIENT_ID env var on the backend.
 *
 * Usage:
 *   const token = await getIdToken();          // returns string | null
 *   const headers = token ? { Authorization: `Bearer ${token}` } : {};
 *   fetch("/your-api", { method: "POST", headers, body: ... });
 *
 * On 401 response, clear the cache and retry once:
 *   if (resp.status === 401) {
 *     _idToken = null; _tokenExpiry = 0;
 *     token = await getIdToken();
 *     resp = await fetch("/your-api", { headers: token ? { Authorization: `Bearer ${token}` } : {} , ... });
 *   }
 */

const GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com";

let _idToken = null;
let _tokenExpiry = 0;
const _tokenWaiters = [];

function _onGoogleCredential(response) {
  try {
    const payload = JSON.parse(atob(response.credential.split('.')[1]));
    _tokenExpiry = payload.exp * 1000;
  } catch {
    _tokenExpiry = Date.now() + 3_600_000;
  }
  _idToken = response.credential;
  _tokenWaiters.splice(0).forEach(fn => fn(_idToken));
}

// Called by the GSI library once it has loaded (via onGoogleLibraryLoad hook).
window.onGoogleLibraryLoad = function () {
  google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: _onGoogleCredential,
    auto_select: true,          // silent sign-in when Google session exists
    use_fedcm_for_prompt: true,
  });
  google.accounts.id.prompt();
};

/**
 * Returns a Promise<string|null>.
 * Resolves immediately if a cached token is still valid;
 * otherwise waits up to 5 s for GSI to deliver one.
 */
function getIdToken() {
  if (_idToken && Date.now() < _tokenExpiry - 60_000) {
    return Promise.resolve(_idToken);
  }
  if (typeof google !== "undefined" && google.accounts?.id) {
    google.accounts.id.prompt();
  }
  return new Promise(resolve => {
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) { settled = true; resolve(null); }
    }, 5_000);
    _tokenWaiters.push(token => {
      if (!settled) { settled = true; clearTimeout(timer); resolve(token); }
    });
  });
}
