import os
from functools import lru_cache


class Settings:
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/signalshift")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.jwt_secret = os.getenv("JWT_SECRET", "change-me")

    async def initialize(self):
        # Placeholder: setup DB, Redis pools, logging contexts, etc.
        pass

    async def shutdown(self):
        # Placeholder: close pools.
        pass


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
