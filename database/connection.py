import logging
from contextlib import contextmanager
from typing import Generator

import pyodbc

from config.database import db_settings
from exceptions import AppError, DatabaseError


logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, connection_string: str | None = None) -> None:
        self.connection_string = (
            connection_string
            or db_settings.connection_string()
        )

    def get_connection(self) -> pyodbc.Connection:
        """
        Tạo một kết nối mới tới SQL Server.

        autocommit=False để transaction được quản lý rõ ràng.
        """
        logger.debug("Opening database connection")

        try:
            return pyodbc.connect(
                self.connection_string,
                autocommit=False,
                timeout=5,
            )
        except pyodbc.Error as exc:
            raise DatabaseError(
                "Không thể kết nối cơ sở dữ liệu. Vui lòng kiểm tra SQL Server, "
                "tên database và ODBC Driver 18 for SQL Server."
            ) from exc

    @contextmanager
    def transaction(
        self,
    ) -> Generator[pyodbc.Connection, None, None]:
        """
        Context manager quản lý transaction.

        Thành công:
            commit

        Có exception:
            rollback
            raise lại exception
        """
        connection = self.get_connection()

        try:
            yield connection

            connection.commit()

            logger.debug(
                "Database transaction committed"
            )

        except AppError:
            connection.rollback()

            logger.debug(
                "Database transaction rolled back for an expected application error"
            )

            raise

        except Exception:
            connection.rollback()

            logger.exception(
                "Database transaction rolled back"
            )

            raise

        finally:
            connection.close()

            logger.debug(
                "Database connection closed"
            )


db_manager = DatabaseManager()
