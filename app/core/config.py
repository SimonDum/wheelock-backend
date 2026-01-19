from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ENV: str = "dev"

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    SENSOR_API_KEY: str

    # Email configuration
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str
    MAIL_PORT: int = 587
    MAIL_SERVER: str
    MAIL_FROM_NAME: str = "Wheelock Application"
    ADMIN_EMAIL: str

    # MinIO / S3 Configuration
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "images-public"
    MINIO_USE_SSL: bool = False
    MINIO_PUBLIC_ENDPOINT: str = "http://localhost:9000"  # Pour les URLs publiques

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
