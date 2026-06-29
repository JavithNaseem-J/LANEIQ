from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"
    MARINETRAFFIC_KEY: str = ""
    MLFLOW_URI: str = "http://localhost:5000"
    S3_BUCKET: str = "freightmind-bucket"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
