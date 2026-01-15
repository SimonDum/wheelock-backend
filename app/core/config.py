from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "dev"

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES_ADMIN: int = 30
    JWT_EXPIRE_MINUTES_ANON: int = 60

    SENSOR_API_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()
