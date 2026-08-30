import os

from config.settings import BASE_DIR


class DatabaseSettings:
    SERVER = os.getenv("DB_SERVER", r".\SQLEXPRESS")
    DATABASE = os.getenv("DB_NAME", "student_support_db")

    DRIVER = os.getenv(
        "DB_DRIVER",
        "ODBC Driver 18 for SQL Server",
    )

    TRUSTED_CONNECTION = os.getenv(
        "DB_TRUSTED_CONNECTION",
        "yes",
    )

    TRUST_SERVER_CERTIFICATE = os.getenv(
        "DB_TRUST_SERVER_CERTIFICATE",
        "yes",
    )

    @classmethod
    def connection_string(cls) -> str:
        return (
            f"DRIVER={{{cls.DRIVER}}};"
            f"SERVER={cls.SERVER};"
            f"DATABASE={cls.DATABASE};"
            f"Trusted_Connection={cls.TRUSTED_CONNECTION};"
            f"TrustServerCertificate={cls.TRUST_SERVER_CERTIFICATE};"
        )


db_settings = DatabaseSettings()