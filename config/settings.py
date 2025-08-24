from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # DB
    db_host: str = Field(..., alias="DB_HOST")
    db_port: int = Field(..., alias="DB_PORT")
    db_user: str = Field(..., alias="DB_USER")
    db_password: str = Field("", alias="DB_PASSWORD")
    db_name: str = Field(..., alias="DB_NAME")

    # JWT / Secret
    secret_key: str = Field(..., alias="JWT_SECRET")
    jwt_expires_min: int = Field(1440, alias="JWT_EXPIRES_MIN")

    # NAVER
    naver_client_id: str | None = Field(None, alias="NAVER_CLIENT_ID")
    naver_client_secret: str | None = Field(None, alias="NAVER_CLIENT_SECRET")

    # Qdrant
    qdrant_host: str = Field("localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(6333, alias="QDRANT_PORT")

    # Thresholds
    menu_sim_threshold: float = Field(0.3, alias="MENU_SIM_THRESHOLD")
    packaging_sim_threshold: float = Field(0.5, alias="PACKAGING_SIM_THRESHOLD")

    # Admin
    admin_id: str | None = Field(None, alias="ADMIN_ID")
    admin_password: str | None = Field(None, alias="ADMIN_PASSWORD")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
