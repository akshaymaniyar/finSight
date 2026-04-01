from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    gmail_client_id: str = Field(default="", alias="GMAIL_CLIENT_ID")
    gmail_client_secret: str = Field(default="", alias="GMAIL_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="http://localhost:8000/api/auth/callback", alias="GOOGLE_REDIRECT_URI")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    jwt_secret: str = Field(default="finsight-dev-secret", alias="JWT_SECRET")
    mysql_host: str = Field(default="localhost", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="root", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="finsight", alias="MYSQL_DATABASE")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    port: int = Field(default=8000, alias="PORT")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+mysqlconnector://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    class Config:
        env_file = ".env"
        populate_by_name = True


settings = Settings()
