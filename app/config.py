from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    database_url: str
    rabbitmq_url: str

    api_key: str

    # retry
    max_attempts: int = 3
    retry_base_delay_sec: int = 2  # экспонента


settings = Settings()