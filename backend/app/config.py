import os


def _load_env_file() -> None:
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


_load_env_file()


class Settings:
    app_name: str = "Hotel Monitor API"
    app_version: str = "0.2.0"
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./hotel_monitor.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_eager: bool = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
    auto_create_tables: bool = os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true"
    ai_provider: str = os.getenv("AI_PROVIDER", "mock")
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    push_channel: str = os.getenv("PUSH_CHANNEL", "console")
    push_webhook_url: str = os.getenv("PUSH_WEBHOOK_URL", "")

    def validate(self) -> None:
        if not self.jwt_secret_key or self.jwt_secret_key == "dev-secret-change-me":
            if os.getenv("APP_ENV", "dev") == "prod":
                raise ValueError("JWT_SECRET_KEY must be set in production")
        if self.jwt_expire_minutes <= 0:
            raise ValueError("JWT_EXPIRE_MINUTES must be positive")


settings = Settings()
