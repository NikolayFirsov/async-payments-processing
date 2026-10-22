from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str
    rabbitmq_url: str

    api_key: str

    # Consumer/retry
    max_attempts: int = 3
    retry_base_delay_sec: int = 2  # экспонента
    webhook_timeout_sec: float = 10.0
    processing_min_sec: float = 2.0
    processing_max_sec: float = 5.0
    success_rate: float = 0.9

    # Outbox
    outbox_poll_interval_sec: float = 1.0
    outbox_batch_size: int = 50


settings = Settings()