from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    # JWT / OIDC auth (disabled by default for local dev and tests)
    auth_enabled: bool = False
    google_client_id: str = ""
    # Set via env var as a JSON array, e.g. ALLOWED_EMAILS='["a@example.com","b@example.com"]'.
    # A comma-separated string is NOT accepted (pydantic-settings raises SettingsError).
    allowed_emails: list[str] = []


settings = Settings()
