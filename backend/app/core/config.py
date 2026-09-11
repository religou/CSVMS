"""应用配置管理."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，通过环境变量注入."""

    # Application
    APP_NAME: str = "CSVS"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "csvs"
    DB_PASSWORD: str = ""
    DB_NAME: str = "csvs"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # JWT
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Security
    PASSWORD_MIN_LENGTH: int = 8
    LOGIN_FAIL_LOCK_THRESHOLD: int = 5
    LOGIN_FAIL_LOCK_MINUTES: int = 15
    SESSION_TIMEOUT_MINUTES: int = 30

    # SMTP / Notification
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = False
    SMTP_FROM_ADDRESS: str = ""
    FRONTEND_LOGIN_URL: str = "http://localhost:5173/login"
    MEMBER_ADDED_EMAIL_SUBJECT: str = "{project_name} 项目成员通知"
    MEMBER_ADDED_EMAIL_BODY: str = (
        "您好 {full_name}，\n\n您已被添加至项目「{project_name}」，角色：{role_label}。\n登录地址：{login_url}\n"
    )
    MEMBER_ROLE_CHANGED_EMAIL_SUBJECT: str = "{project_name} 项目角色变更通知"
    MEMBER_ROLE_CHANGED_EMAIL_BODY: str = (
        "您好 {full_name}，\n\n您在项目「{project_name}」中的角色已变更为：{role_label}。\n登录地址：{login_url}\n"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
