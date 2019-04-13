"""Access control for SQL databases and tables."""

import abc
import pathlib
import sqlite3

from typing import Iterable
from typing import List
from typing import Tuple


class SQLiteDatabase(object):
    """SQLite root database class with management methods to manipulate tables through SQL queries.

    Attributes:
        path: Path to database file. May be ":memory:" to create database in RAM.
    """
    NO_ENTRY = -1

    def __init__(self, path: str) -> None:
        """Setup the DB to allow connections to be made."""
        self._connection = None
        self.path = path

    def close(self) -> bool:
        """Disconnects the database from the storage.

        Returns:
            True if the database is open and is successfully closed, False if the database is not open.
        """
        if not self.is_open():
            return False
        self._connection.close()
        self._connection = None
        return True

    def create(self) -> None:
        """Creates database on the local filesystem."""
        sqlite3.connect(self.path).close()

    def execute(self, statement: str, values: Iterable = ()):
        """Executes a SQL statement on the database.

        No form of validation or injection prevention is performed with this method. This method should only be used by
        internal processes with hardcoded statements.

        Args:
            statement: A SQL command.
            values: Optional parameters to pass to SQLite cursor.

        Returns:
            True is statement is executed, False if database is not open.
        """
        if not self.is_open():
            return False
        cursor = self._connection.cursor()
        cursor.execute(statement, values)
        cursor.close()
        return True

    def get_version(self) -> int:
        """Finds the version stored in the database.

        Returns:
            The stored version in the database.
        """
        if not self.is_open():
            return SQLiteDatabase.NO_ENTRY
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA user_version')
        row = cursor.fetchone()
        version = row[0]
        cursor.close()
        return int(version)

    def insert(self, table_name: str, entry: dict) -> int:
        """Performs a SQL INSERT statement on a table.

        Args:
            table_name: A table name in the database.
            entry: Data to store in the database with keys as columns and values as row data.

        Returns:
            The total amount of rows inserted into database or -1 if an error occurred.
        """
        if not self.is_open() or not entry:
            return SQLiteDatabase.NO_ENTRY
        value_groups = entry.items()
        columns = self.qmark_values(value_groups, True, False)
        rows = self.qmarks(len(value_groups))
        row_data = self.qmark_values(value_groups, False, True)
        statement = f'INSERT OR IGNORE INTO {table_name} {columns} VALUES {rows}'

        cursor = self._connection.cursor()
        cursor.execute(statement, row_data)
        self._connection.commit()
        count = cursor.rowcount
        cursor.close()
        return count

    def is_open(self) -> bool:
        """Checks if a connection is already open to the database.

        Returns:
            True if connection exists, False otherwise.
        """
        return self._connection is not None

    def open(self, flags: str) -> bool:
        """Establishes the database connection to the storage.

        Connection will remain open until close() is called.

        Args:
            flags: Option flags to apply to SQLite connection.

        Returns:
            True if no connection is open and new connection is successful, False if the connection is already open.
        """
        if not self.is_open():
            path = f'file:{self.path}' if self.path != ':memory:' else ':memory:'
            self._connection = sqlite3.connect(f'{path}?{flags}', uri=True)
            return True
        return False

    @staticmethod
    def prepare_columns(value_groups: Iterable[tuple]) -> str:
        """Converts key:value pairs into a SQL compatible portion of query statement replacing values with '?'s.

        Args:
            value_groups: Tuples representing column to value pairs.

        Returns:
            A string in SQL query format with the original column names saved and values replaced with '?'s.
        """
        return ','.join(str(f'{key} = ?') for key, _ in value_groups)

    @staticmethod
    def qmark_values(value_groups: Iterable[tuple], columns: bool = True, rows: bool = True) -> Tuple[str]:
        """Converts key:value pairs into a SQL compatible parameter list to be passed with a query statement.

        The result should be used in combination with a qmarks() of the same length.

        Args:
            value_groups: Column to value pairs.
            columns: Whether the keys should be converted.
            rows: Whether the values should be converted.

        Returns:
            The final values maintaining order of the groups that were passed.
        """
        qmarks = ()
        for key, value in value_groups:
            if columns:
                qmarks += (key,)
            if rows:
                qmarks += (value,)
        return qmarks

    @staticmethod
    def qmarks(count: int) -> str:
        """Provides SQL statement formatted list of question marks to be replaced with parameters in a SQL query.

        Args:
            count: The total amount of '?'s.

        Returns:
            A string in SQL query format with requested amount of '?'s.
        """
        qmarks = ','.join(['?' for _ in range(0, count)])
        return f'({qmarks})'

    def remove(self, table_name: str, where_clause: str, where_args: Iterable) -> int:
        """Performs a SQL DELETE statement on a table.

        Args:
            table_name: A table name in the database.
            where_clause: The conditional statements for valid rows with question marks for values.
            where_args: Values to pass into the question marks from the where clause.

        Returns:
            The total amount of rows removed, or -1 if an error occurred.
        """
        if not self.is_open() or not where_clause or not where_args:
            return SQLiteDatabase.NO_ENTRY
        statement = f'DELETE FROM {table_name} WHERE {where_clause}'

        cursor = self._connection.cursor()
        cursor.execute(statement, where_args)
        self._connection.commit()
        count = cursor.rowcount
        cursor.close()
        return count

    def select(self, table_name: str, columns: Iterable[str], selection: str, selection_args: Iterable,
               order_by: str = None) -> List[dict]:
        """Performs a SQL SELECT statement on a table.

        Args:
            table_name: A table name in the database.
            columns: Collection of strings for columns to pull from table.
            selection: The conditional statements for valid rows with question marks for values.
            selection_args: Values to pass into the question marks from the selection statement.
            order_by: The column name to sort by.

        Returns:
            A list dictionaries with column names as keys, and row values as values
        """
        if not self.is_open():
            return []

        columns_data = ','.join(str(column) for column in columns)
        statement = f'SELECT {columns_data} FROM {table_name}'
        if selection:
            statement = f'{statement} WHERE {selection}'
        else:
            selection_args = []

        if order_by:
            statement += f'{statement} ORDER BY {order_by}'

        cursor = self._connection.cursor()
        rows = cursor.execute(statement, selection_args).fetchall()
        cursor.close()

        # Expand wildcard into table columns
        if columns == ('*',):
            columns = tuple(title[0] for title in cursor.description)
        return [{column: result for column, result in zip(columns, row)} for row in rows]

    def set_version(self, version: int) -> bool:
        """Applies version number to database schema.

        Args:
            version: The new version.

        Returns:
            True if new version matches supplied version after update, False if database is closed or versions mismatch.
        """
        if not self.is_open():
            return False
        cursor = self._connection.cursor()
        cursor.execute(f'PRAGMA user_version = {int(version)}')
        self._connection.commit()
        cursor.close()
        matches = self.get_version() == version
        return matches

    def update(self, table_name: str, entry: dict, where_clause: str, where_args: Iterable) -> int:
        """Performs a SQL UPDATE statement on a table.

        Args:
            table_name: A table name in the database.
            entry: Data to store in the database with keys as columns and values as row data.
            where_clause: The conditional statements for valid rows with question marks for values.
            where_args: Values to pass into the question marks from the where clause.

        Returns:
            The total amount of rows updated, or -1 if an error occurred.
        """
        if not self.is_open() or not where_clause or not where_args or not entry:
            return SQLiteDatabase.NO_ENTRY
        value_groups = entry.items()
        columns = self.prepare_columns(value_groups)
        row_data = self.qmark_values(value_groups, False, True) + where_args
        statement = f'UPDATE {table_name} SET {columns} WHERE {where_clause}'

        cursor = self._connection.cursor()
        cursor.execute(statement, row_data)
        self._connection.commit()
        count = cursor.rowcount
        cursor.close()
        return count


class SQLiteHelper(object, metaclass=abc.ABCMeta):
    """SQLite helper class used to manage creation, upgrades, downgrades, and simplify queries to databases.

    Attributes:
        path: Path to database file. May be ":memory:" to create database in RAM.
        database: A shared SQLiteDatabase between all operations.
        database_version: An integer representing the version of the database used for creation and updates.
    """

    def __init__(self, path: str, database_version: int = 1) -> None:
        """Initializes the helper."""
        self.path = path
        self.database = None
        self.database_version = database_version

        self._init_db(database_version)
        self.open('mode=rw')
        self.upgrade_db(database_version)
        self.downgrade_db(database_version)
        self.close()

    @abc.abstractmethod
    def _get_tables_to_create(self) -> List[str]:
        """Provides SQL queries to be run when tables are created in the database.

        Returns:
            A list of SQL "CREATE TABLE" commands which will be executed directly on the database.
        """

    def _init_db(self, version: int) -> None:
        """Initializes the database from storage including creating tables if necessary.

        Args:
            version: Initial version number of the database when newly created.
        """
        path = pathlib.Path(self.path).expanduser().absolute() if self.path != ':memory:' else ':memory:'
        self.database = SQLiteDatabase(str(path))

        # DB must be instantiated after checking path to prevent accidental creation
        if path == ':memory:' or not path.is_file():
            if path != ':memory:':
                parent = path.parent
                if not parent.is_dir():
                    parent.mkdir(parents=True, exist_ok=True)
            self.database.create()

            # Before returning, open the database to set the initial version and create tables
            self.open()
            self.database.set_version(version)
            for create_table in self._get_tables_to_create():
                self.database.execute(create_table)
            self.close()

    def close(self) -> bool:
        """Closes the shared database.

        Returns:
            True if the database is open and is successfully closed, False if the database is not open.
        """
        closed = self.database.close()
        return closed

    @abc.abstractmethod
    def downgrade_db(self, old_version: int) -> None:
        """Verifies the current version against a specified version to perform downgrade modification tasks.

        This should in theory always reverse the process applied in the upgrade_db() method, unless attempting to
        correct a poorly designed upgrade.

        Args:
            old_version: The version that the database should be after maintenance.
        """

    def get_readable_db(self) -> SQLiteDatabase:
        """Opens the database in read only mode.

        Returns:
            The SQLiteDatabase for this helper.
        """
        self.open('mode=ro')
        return self.database

    def get_writable_db(self) -> SQLiteDatabase:
        """Opens the database in read and write mode.

        Returns:
            The SQLiteDatabase for this helper.
        """
        self.open('mode=rw')
        return self.database

    def open(self, flags: str = 'mode=rw') -> None:
        """Opens the shared database.

        Args:
            flags: Option flags to apply to SQLite connection.

        Returns:
            True if no connection is open and new connection is successful, False if the connection is already open.
        """
        db = self.database.open(flags)
        return db

    @abc.abstractmethod
    def upgrade_db(self, new_version: int) -> None:
        """Verifies the current version against a specified version to perform upgrade modification tasks.

        Args:
            new_version: The version that the database should be after maintenance.
        """


class SQLiteTable(object, metaclass=abc.ABCMeta):
    """SQLite convenience class used to manage creation, upgrades, downgrades, and simplify queries to tables.

    Attributes:
        path: A string path to database file. May be ":memory:" to create database in RAM.
    """

    def __init__(self, path: str) -> None:
        """Setup a table to be used with a database."""
        self.path = path
        self._name = self._get_table_name()
        self._helper = self._init_helper()

    @abc.abstractmethod
    def _get_table_name(self) -> str:
        """Creates a string for the table to use with all SQL queries.

        This method should only be called once during initialization of the object and should never be called manually.

        Returns:
            A string representing the name of this table in a database which will be used for all queries.
        """

    @abc.abstractmethod
    def _init_helper(self) -> SQLiteHelper:
        """Creates a database helper to manage all connectivity to storage during queries.

        This method should only be called once during initialization of the object and should never be called manually.

        Returns:
            A SQLiteHelper which will be used to manage all database access requests.
        """

    def add(self, entry: dict) -> int:
        """Performs a SQL INSERT statement.

         Args:
             entry: Data to store in the database with keys as columns and values as row data.

         Returns:
             The total amount of rows inserted into database or -1 if an error occurred.
         """
        database = self.get_writable_db()
        count = database.insert(self._name, entry)
        database.close()
        return count

    def get(self, columns: Iterable[str], selection: str = None, selection_args: Iterable = None,
            order_by: str = None) -> List[dict]:
        """Performs a SQL SELECT statement.

        Args:
            columns: Columns to pull from table.
            selection: Conditional statements for valid rows with question marks for values.
            selection_args: Values to pass into the question marks from the selection statement.
            order_by: Column name to sort by.

        Returns:
            Results with column names as keys, and row values as values.
        """
        database = self.get_readable_db()
        entries = database.select(self._name, columns, selection, selection_args, order_by)
        database.close()
        return entries

    def get_readable_db(self) -> SQLiteDatabase:
        """Requests a read and write database from the SQLiteHelper.

        Returns:
            A Database in read and write mode.
        """
        db = self._helper.get_readable_db()
        return db

    @staticmethod
    @abc.abstractmethod
    def get_table_create_statement() -> str:
        """Creates a string to be used when the table is initially created on the storage.

        Returns:
            A SQL string that can be executed on a database to create the table.
        """

    def get_writable_db(self) -> SQLiteDatabase:
        """Requests a read only database from the SQLiteHelper.

        Returns:
            A Database in read only mode.
        """
        db = self._helper.get_writable_db()
        return db

    def remove(self, where_clause: str, where_args: Iterable) -> int:
        """Performs a SQL UPDATE statement.

        Args:
            where_clause: The conditional statements for valid rows with question marks for values.
            where_args: Values to pass into the question marks from the where clause.

        Returns:
            The total amount of rows updated, or -1 if an error occurred.
        """
        database = self.get_writable_db()
        count = database.remove(self._name, where_clause, where_args)
        database.close()
        return count

    def update(self, entry: dict, where_clause: str, where_args: Iterable) -> int:
        """Performs a SQL UPDATE statement.

        Args:
            entry: Data to store in the database with keys as columns and values as row data.
            where_clause: The conditional statements for valid rows with question marks for values.
            where_args: Values to pass into the question marks from the where clause.

        Returns:
            The total amount of rows updated, or -1 if an error occurred.
        """
        database = self.get_writable_db()
        count = database.update(self._name, entry, where_clause, where_args)
        database.close()
        return count
