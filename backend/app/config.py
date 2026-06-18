from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: str = "/data"
    initial_admin_username: str | None = None
    initial_admin_password: str | None = None
    session_ttl_days: int = 14
    session_max_ttl_days: int = 90
    max_upload_mb: int = 15

    @property
    def database_path(self) -> str:
        return f"{self.data_dir}/scatterbooks.db"

    @property
    def images_dir(self) -> str:
        return f"{self.data_dir}/images"


settings = Settings()
