import json
import urllib.parse
from pathlib import Path


class SQLConnection:
    """
    A class to manage the Connection to  database.

    Args:
        host: SQL Database host.
        port: SQL Database port.
        user: SQL Database user.
        password: SQL Database user password.
        database: SQL Database name.
        **kwargs: Additional arguments to pass to psycopg2.connect.
    """

    def __init__(
            self,
            host: str,
            user: str,
            password: str,
            database: str,
            **kwargs
    ) -> None:
        encoded_password = urllib.parse.quote_plus(password)

        # build URI string
        self._uri = f"mysql://{user}:{encoded_password}@{host}/{database}"

    @classmethod
    def from_config(cls, file_path: Path) -> "SQLConnection":
        """
        Load the database configuration from a JSON file.

        Args:
            file_path: Path to JSON file.
        """
        # load config file
        data = json.loads(file_path.read_text())

        # create instance with config data
        return cls(**data)

    def get_uri(self) -> str:
        # return the database URI
        return self._uri
