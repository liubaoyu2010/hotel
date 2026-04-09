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
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./hotel_monitor.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    celery_eager: bool = os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
    auto_create_tables: bool = os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true"
    ai_provider: str = os.getenv("AI_PROVIDER", "mock")
    ai_api_key: str = os.getenv("AI_API_KEY", "")
    ai_base_url: str = os.getenv("AI_BASE_URL", "https://api.deepseek.com")
    ai_model: str = os.getenv("AI_MODEL", "deepseek-chat")
    push_channel: str = os.getenv("PUSH_CHANNEL", "console")
    push_webhook_url: str = os.getenv("PUSH_WEBHOOK_URL", "")
    push_serverchan_key: str = os.getenv("PUSH_SERVERCHAN_KEY", "")
    push_wxpusher_token: str = os.getenv("PUSH_WXPUSHER_TOKEN", "")
    push_wxpusher_uids: str = os.getenv("PUSH_WXPUSHER_UIDS", "")
    activity_collect_enabled: bool = os.getenv("ACTIVITY_COLLECT_ENABLED", "true").lower() == "true"
    activity_default_radius_km: float = float(os.getenv("ACTIVITY_DEFAULT_RADIUS_KM", "3.0"))
    activity_city_override: str = os.getenv("ACTIVITY_CITY_OVERRIDE", "")
    amap_api_key: str = os.getenv("AMAP_API_KEY", "")

    def validate(self) -> None:
        if not self.jwt_secret_key or self.jwt_secret_key == "dev-secret-change-me":
            if os.getenv("APP_ENV", "dev") == "prod":
                raise ValueError("JWT_SECRET_KEY must be set in production")
        if self.jwt_expire_minutes <= 0:
            raise ValueError("JWT_EXPIRE_MINUTES must be positive")


settings = Settings()
