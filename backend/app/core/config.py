from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    # JWT / OIDC auth (disabled by default for local dev and tests)
    auth_enabled: bool = False
    google_client_id: str = ""
    # Comma-separated list; also accepts a JSON array via env var
    allowed_emails: list[str] = []


settings = Settings()
