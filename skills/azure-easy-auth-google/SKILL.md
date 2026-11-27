---
name: azure-easy-auth-google
description: Azure Container Apps 上の Web アプリ（静的フロント＋nginx と FastAPI バックエンド）を、特定の Google アカウントだけが使えるようにする。Easy Auth、nginx のメール許可リスト、GSI のサイレントサインイン、バックエンドでの Google JWT 検証の4層を入れる。「Google ログインで自分だけ使えるようにしたい」「Container Apps に認証を付けたい」「バックエンド API を Google アカウントで保護したい」ときに使う。
---

# Azure Easy Auth + Google JWT（4層認証）

参照実装は `${CLAUDE_PLUGIN_ROOT}` にある。コードは一から書かず、ここにあるファイルを新しいプロジェクトにコピーして合わせる。

- 最終検証: 2026-11-26（`backend/tests` の 8件が通ることを確認。Azure への実デプロイは 2026-06-02 の初版時点のもの）
- 主な依存: fastapi>=0.115、python-jose[cryptography]>=3.3、pydantic-settings>=2.0、Python>=3.11

## 使うかどうかの判断

使う:
- Azure Container Apps に置く。
- 利用者は少数の決まった Google アカウント（自分や数人）。
- フロント（nginx）とバックエンド（FastAPI）が別のコンテナ。

使わない（別の方法を考える）:
- 不特定多数のユーザー登録やロール管理が必要 → 本格的な IdP（Entra External ID、Auth0 など）。
- Microsoft アカウントでログインさせたい → Easy Auth のプロバイダーを `aad` にする。nginx とバックエンドの層の考え方は流用できるが、JWT 検証部分（Google JWKS 前提）は作り直しになる。
- バックエンドを外部に公開しない（フロントからの内部通信だけ） → 第3・4層は省いて、Easy Auth と nginx だけでもよい。

## 構成と、そうしている理由

```
[Browser]
  ↓
[1] Azure Easy Auth   未ログインなら Google ログインへ転送
  ↓ X-MS-CLIENT-PRINCIPAL-NAME
[2] nginx             メール許可リストにない人は 403
  ↓ 静的ファイルを返す
[3] Frontend (GSI)    Google ID トークンをサイレントに取得
  ↓ Authorization: Bearer <id_token>
[4] Backend (FastAPI) Google JWKS で JWT を直接検証
```

- 1・2層はフロントを守り、3・4層はバックエンド API を守る。
- **バックエンドは Azure を信用しない。** バックエンドの URL が直接叩かれても、`X-MS-*` ヘッダーは偽装できるため。Google の公開鍵（JWKS）で署名・aud・iss・`email_verified`・許可リストを自分で確かめる。
- トークンは `Authorization: Bearer` を優先し、なければ Easy Auth が付ける `X-MS-TOKEN-GOOGLE-ID-TOKEN` を使う。

## 適用手順

参照するファイル（`${CLAUDE_PLUGIN_ROOT}` からの相対パス）:

| ファイル | 扱い |
|---|---|
| `backend/app/core/auth.py` | そのままコピー。`require_authorized_user` 依存関数 |
| `backend/app/core/config.py` | 既存の Settings があれば3項目だけ統合 |
| `backend/app/main.py` | 使い方の例（コピー不要） |
| `backend/tests/conftest.py`, `test_auth.py` | テストもコピーし、新プロジェクトで通ることを確かめる |
| `frontend/gsi-auth.js` | コピーして `GOOGLE_CLIENT_ID` を書き換える |
| `frontend/nginx.conf.template` | コピーして許可メールと API のプロキシを追加 |
| `deploy/enable-auth.sh` | コピー（引数で全パラメータを渡す） |

1. 先に新プロジェクトの構成を確認する（`app/core/` の有無、既存の Settings、nginx の設定の置き場所、API のパス）。参照実装と違う場合は、コピー先とインポートのパスを合わせる。
2. バックエンド: `auth.py` と設定を入れ、守りたいエンドポイントに `Depends(require_authorized_user)` を付ける。依存パッケージ（`httpx`、`python-jose[cryptography]`、`pydantic-settings`）を追加する。
3. テストをコピーして通す。
4. フロント: HTML に `<script src="https://accounts.google.com/gsi/client" async defer></script>` と `gsi-auth.js` を入れ、API を呼ぶ前に `await getIdToken()` で取ったトークンを `Authorization: Bearer` で付ける。401 が返ったら `_idToken = null; _tokenExpiry = 0;` でキャッシュを捨てて1回だけ再試行する。
5. nginx: `map` ブロックに許可するメールを書き、API のパスごとに `location` のプロキシを有効にする。
6. ユーザーに Google Cloud Console での作業を頼む: OAuth 2.0 クライアント ID（Web アプリ）を作り、承認済みリダイレクト URI に `https://<FRONTEND_FQDN>/.auth/login/google/callback` を追加する。Client ID と Secret を受け取る（Secret はリポジトリに書かない）。
7. デプロイ後に `deploy/enable-auth.sh <SUBSCRIPTION_ID> <RESOURCE_GROUP> <APP_NAME> <CLIENT_ID> <CLIENT_SECRET>` を実行する。**Azure を変更する操作なので、実行前にユーザーに確認する。**
8. バックエンドの本番環境変数に `AUTH_ENABLED=true`、`GOOGLE_CLIENT_ID`、`ALLOWED_EMAILS` を設定する。

## 落とし穴

- **`ALLOWED_EMAILS` は JSON 配列で書く。** `ALLOWED_EMAILS='["a@example.com","b@example.com"]'`。カンマ区切り（`a@x.com,b@x.com`）は pydantic-settings が `SettingsError` で起動に失敗する（2026-11-26 に確認）。
- **`GOOGLE_CLIENT_ID` は3か所で同じ値にする。** `gsi-auth.js`、バックエンドの環境変数、`enable-auth.sh` の引数。違うと aud の検証で 401 になる。
- **許可リストは nginx の `map` とバックエンドの `ALLOWED_EMAILS` の2か所にある。** 片方だけ直すと、画面は開くのに API が 403、またはその逆になる。
- **ローカルでは nginx が全部 403 を返す。** Easy Auth がなく `X-MS-CLIENT-PRINCIPAL-NAME` が付かないため。ローカルではバックエンドに `http://localhost:8000` で直接アクセスする。`AUTH_ENABLED` の既定値は `false` で、バックエンドの認証は無効になる。
- **`nginx.conf.template` の冒頭コメントには `ALLOWED_EMAIL` 環境変数とあるが、実際の `map` はメールを直接書く形。** 置き換えに使われる環境変数は `${BACKEND_UPSTREAM}` だけ。
- **独自ドメインを付けたら、Google 側のリダイレクト URI にも新しいドメインの `/.auth/login/google/callback` を追加する。** 足りないとログイン後に `redirect_uri_mismatch` になる。
- **Easy Auth（`RedirectToLoginPage`）の動作を curl で確かめるときは、ブラウザらしいヘッダーを付ける。** 素の curl には 401 が返り、`Accept: text/html` と User-Agent を付けたときだけ 302 でログイン画面へ転送される。偽の `X-MS-CLIENT-PRINCIPAL-NAME` を付けても通らないことも確かめておく。
- **README の `pip install -e ".[dev]"` は 2026-11-26 まで失敗していた。** hatchling がパッケージを判別できなかった。`pyproject.toml` に `[tool.hatch.build.targets.wheel] packages = ["app"]` を追加して直した。新プロジェクトで同じ構成にするなら同じ設定が要る。

## 確認

- バックエンドのテストが通る。
- デプロイ後、ブラウザでアクセスすると Google ログインに転送される。許可したアカウントなら画面が出て API も呼べる。
- 許可していないアカウントでは 403 になる（別アカウントで確かめる）。

## 適用が終わったら

参照実装や手順どおりに行かなかった点があれば、ユーザーに伝え、このテンプレートのリポジトリ（https://github.com/SzTk/azure-easy-auth-google-template）の SKILL.md の「落とし穴」かコードへの反映を提案する。反映するときは `.claude-plugin/plugin.json` の `version` を上げる。
