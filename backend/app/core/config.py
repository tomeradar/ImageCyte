from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    UPSTREAM_URL: str = "https://assignment-server-rv-866595813231.us-central1.run.app"
    UPSTREAM_USERNAME: str = "tomer.adar"
    UPSTREAM_PASSWORD: str = "chip2255"
    POLLING_INTERVAL: int = 5
    DATABASE_URL: str = "sqlite:///./microscopy.db"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
