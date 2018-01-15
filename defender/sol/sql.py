import sqlite3
from abc import ABC, abstractmethod
from pathlib import Path


class SQLiteDatabase(object):
    """SQLite root database class with management methods to manipulate tables through SQL queries.

    Attributes:
        path: A string path to database file. May be ":memory:" to create database in RAM.
        _connection: A sqlite3 connection
    """
    NO_ENTRY = -1

    def __init__(self, path):
        self.path = path
        self._connection = None

    def create(self):
        """Creates database on local filesystem."""
        sqlite3.connect(self.path).close()

    def open(self, flags):
        """Establishes the database connection to the storage.

        Connection will remain open until close() is called.

        Args:
            flags: A string representing option flags to apply to SQLite connection

        Returns:
            True if no connection is open and new connection is successful, False if the connection is already open
        """
        if not self.is_open():
            path = 'file:{}'.format(self.path) if self.path != ':memory:' else ':memory:'
            self._connection = sqlite3.connect('{}?{}'.format(path, flags), uri=True)
            return True
        return False

    def is_open(self):
        """Checks if a connection is already open to the database.

        Returns:
            True if connection exists, False otherwise
        """
        return self._connection is not None

    def close(self):
        """Disconnects the database from the storage.

        Returns:
            True if the database is open and is successfully closed, False if the database is not open
        """
        if not self.is_open():
            return False
        self._connection.close()
        self._connection = None
        return True

    def execute(self, statement, values=()):
        """Executes a SQL statement on the database.

        No form of validation or injection prevention is performed with this method. This method should only be used by
        internal processes with hardcoded statements.

        Args:
            statement: A string representing a SQL command
            values: A collection of optional parameters to pass to SQLite cursor

        Returns:
            True is statement is executed, False if database is not open
        """
        if not self.is_open():
            return False
        cursor = self._connection.cursor()
        cursor.execute(statement, values)
        cursor.close()
        return True

    def set_version(self, version):
        """Applies version number to database schema.

        Args:
            version: An integer representing the new version

        Returns:
            True if new version matches supplied version after update, False if database is closed or versions mismatch
        """
        if not self.is_open():
            return False
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA user_version = {}'.format(str(int(version))))
        self._connection.commit()
        cursor.close()

        return self.get_version() == version

    def get_version(self):
        """Finds the version stored in the database.

        Returns:
            An integer representing the stored version in the database
        """
        if not self.is_open():
            return SQLiteDatabase.NO_ENTRY
        cursor = self._connection.cursor()
        cursor.execute('PRAGMA user_version')
        row = cursor.fetchone()
        version = row[0]
        cursor.close()
        return int(version)

    def select(self, table_name, columns, selection, selection_args, order_by=None):
        """Performs a SQL SELECT statement on a table.

        Args:
            table_name: A string representing a table name in the database
            columns: An iterable set of strings for columns to pull from table
            selection: A string representing the conditional statements for valid rows with question marks for values
            selection_args: An iterable set of values to pass into the question marks from the selection statement
            order_by: A string of the column name to order by

        Returns:
            A list dictionaries with column names as keys, and row values as values
        """
        if not self.is_open():
            return []

        columns_data = ','.join(str(column) for column in columns)
        statement = 'SELECT {} FROM {}'.format(columns_data, table_name)
        if selection:
            statement = '{} WHERE {}'.format(statement, selection)
        else:
            selection_args = []

        if order_by:
            statement += '{} ORDER BY {}'.format(statement, order_by)

        cursor = self._connection.cursor()
        rows = cursor.execute(statement, selection_args).fetchall()
        cursor.close()

        # Expand wildcard into table columns
        if columns == ('*',):
            columns = tuple(title[0] for title in cursor.description)
        return [{column: result for column, result in zip(columns, row)} for row in rows]

    def insert(self, table_name, entry):
        """Performs a SQL INSERT statement on a table.

        Args:
            table_name: A string representing a table name in the database
            entry: A dictionary to store in the database with keys as columns and values as row data

        Returns:
            The total amount of rows inserted into database or -1 if an error occurred
        """
        if not self.is_open() or not entry:
            return SQLiteDatabase.NO_ENTRY
        value_groups = entry.items()
        columns = self.qmark_values(value_groups, True, False)
        rows = self.qmarks(len(value_groups))
        row_data = self.qmark_values(value_groups, False, True)
        statement = 'INSERT OR IGNORE INTO {} {} VALUES {}'.format(table_name, columns, rows)

        cursor = self._connection.cursor()
        cursor.execute(statement, row_data)
        self._connection.commit()
        count = cursor.rowcount
        cursor.close()
        return count

    def update(self, table_name, entry, where_clause, where_args):
        """Performs a SQL UPDATE statement on a table.

        Args:
            table_name: A string representing a table name in the database
            entry: A dictionary to store in the database with keys as columns and values as row data
            where_clause: A string representing the conditional statements for valid rows with question marks for values
            where_args: An iterable set of values to pass into the question marks from the where clause

        Returns:
            The total amount of rows updated, or -1 if an error occurred
        """
        if not self.is_open() or not where_clause or not where_args or not entry:
            return SQLiteDatabase.NO_ENTRY
        value_groups = entry.items()
        columns = self.prepare_columns(value_groups)
        row_data = self.qmark_values(value_groups, False, True) + where_args
        statement = 'UPDATE {} SET {} WHERE {}'.format(table_name, columns, where_clause)

        cursor = self._connection.cursor()
        cursor.execute(statement, row_data)
        self._connection.commit()
        count = cursor.rowcount
        cursor.close()
        return count

    def remove(self, table_name, where_clause, where_args):
        """Performs a SQL DELETE statement on a table.

        Args:
            table_name: A string representing a table name in the database
            where_clause: A string representing the conditional statements for valid rows with question marks for values
            where_args: An iterable set of values to pass into the question marks from the where clause

        Returns:
            The total amount of rows removed, or -1 if an error occurred
        """
        if not self.is_open() or not where_clause or not where_args:
            return SQLiteDatabase.NO_ENTRY
        statement = 'DELETE FROM {} WHERE {}'.format(table_name, where_clause)

        cursor = self._connection.cursor()
        cursor.execute(statement, where_args)
        self._connection.commit()
        count = cursor.rowcount
        cursor.close()
        return count

    @staticmethod
    def prepare_columns(value_groups):
        """Converts key:value pairs into a SQL compatible portion of query statement replacing values with '?'s.

        Args:
            value_groups: An iterable of tuples representing column to value pairs

        Returns:
            A string in SQL query format with the original column names saved and values replaced with '?'s
        """
        return ','.join(str('{} = ?'.format(key)) for key, _ in value_groups)

    @staticmethod
    def qmarks(count):
        """Provides SQL statement formatted list of question marks to be replaced with parameters in a SQL query.

        Args:
            count: An integer to determine the total amount of '?'s

        Returns:
            A string in SQL query format with requested amount of '?'s
        """
        return '({})'.format(','.join('?' for i in range(0, count)))

    @staticmethod
    def qmark_values(value_groups, columns=True, rows=True):
        """Converts key:value pairs into a SQL compatible parameter list to be passed with a query statement.

        The result should be used in combination with a qmarks() of the same length.

        Args:
            value_groups: An iterable of tuples representing column to value pairs
            columns: Boolean to determine if the keys should be converted
            rows: Boolean to determine if the values should be converted

        Returns:
            An iterable with final values maintaining order of the groups that were passed.
        """
        qmarks = ()
        for key, value in value_groups:
            if columns:
                qmarks += (key,)
            if rows:
                qmarks += (value,)
        return qmarks


class SQLiteTable(ABC):
    """SQLite convenience class used to manage creation, upgrades, downgrades, and simplify queries to tables.

    Attributes:
        path: A string path to database file. May be ":memory:" to create database in RAM.
        _name: A string representing the name of a single table in the database
        _helper: A SQLiteHelper responsible for handling database retrieval
    """

    def __init__(self, path):
        self.path = path
        self._name = self._get_table_name()
        self._helper = self._init_helper()

    @abstractmethod
    def _init_helper(self):
        """Creates a database helper to manage all connectivity to storage during queries.

        This method should only be called once during initialization of the object and should never be called manually.

        Returns:
            A SQLiteHelper which will be used to manage all database access requests
        """
        pass

    @abstractmethod
    def _get_table_name(self):
        """Creates a string for the table to use with all SQL queries.

        This method should only be called once during initialization of the object and should never be called manually.

        Returns:
            A string representing the name of this table in a database which will be used for all queries
        """
        pass

    @staticmethod
    @abstractmethod
    def get_table_create_statement():
        """Creates a string to be used when the table is initially created on the storage.

        Returns:
            A SQL string that can be executed on a database to create the table
        """
        pass

    def get_readable_db(self):
        """Requests a read and write database from the SQLiteHelper

        Returns:
            A SQLiteDatabase in read and write mode
        """
        return self._helper.get_readable_db()

    def get_writable_db(self):
        """Requests a read only database from the SQLiteHelper

        Returns:
            A SQLiteDatabase in read only mode
        """
        return self._helper.get_writable_db()

    def get(self, columns, selection=None, selection_args=None, order_by=None):
        """Performs a SQL SELECT statement.

        Args:
            columns: An iterable set of strings for columns to pull from table
            selection: A string representing the conditional statements for valid rows with question marks for values
            selection_args: An iterable set of values to pass into the question marks from the selection statement
            order_by: A string of the column name to order by

        Returns:
            A list dictionaries with column names as keys, and row values as values
        """
        database = self.get_readable_db()
        entries = database.select(self._name, columns, selection, selection_args, order_by)
        database.close()
        return entries

    def add(self, entry):
        """Performs a SQL INSERT statement.

         Args:
             entry: A dictionary to store in the database with keys as columns and values as row data

         Returns:
             The total amount of rows inserted into database or -1 if an error occurred
         """
        database = self.get_writable_db()
        count = database.insert(self._name, entry)
        database.close()
        return count

    def update(self, entry, where_clause, where_args):
        """Performs a SQL UPDATE statement.

        Args:
            entry: A dictionary to store in the database with keys as columns and values as row data
            where_clause: A string representing the conditional statements for valid rows with question marks for values
            where_args: An iterable set of values to pass into the question marks from the where clause

        Returns:
            The total amount of rows updated, or -1 if an error occurred
        """
        database = self.get_writable_db()
        count = database.update(self._name, entry, where_clause, where_args)
        database.close()
        return count

    def remove(self, where_clause, where_args):
        """Performs a SQL UPDATE statement.

        Args:
            where_clause: A string representing the conditional statements for valid rows with question marks for values
            where_args: An iterable set of values to pass into the question marks from the where clause

        Returns:
            The total amount of rows updated, or -1 if an error occurred
        """
        database = self.get_writable_db()
        count = database.remove(self._name, where_clause, where_args)
        database.close()
        return count


class SQLiteHelper(ABC):
    """SQLite helper class used to manage creation, upgrades, downgrades, and simplify queries to databases.

    Attributes:
        path: A string path to database file. May be ":memory:" to create database in RAM.
        database: A shared SQLiteDatabase between all operations
    """

    def __init__(self, path, database_version):
        self.path = path
        self.database = None

        self._init_db(database_version)
        self.open('mode=rw')
        self.upgrade_db(database_version)
        self.downgrade_db(database_version)
        self.close()

    def open(self, flags='mode=rw'):
        """Opens the shared database.

        Args:
            flags: A string representing option flags to apply to SQLite connection

        Returns:
            True if no connection is open and new connection is successful, False if the connection is already open
        """
        return self.database.open(flags)

    def close(self):
        """Closes the shared database.

        Returns:
            True if the database is open and is successfully closed, False if the database is not open
        """
        return self.database.close()

    def get_writable_db(self):
        """Opens the database in read and write mode.

        Returns:
            The SQLiteDatabase for this helper
        """
        self.open('mode=rw')
        return self.database

    def get_readable_db(self):
        """Opens the database in read only mode.

        Returns:
            The SQLiteDatabase for this helper
        """
        self.open('mode=ro')
        return self.database

    def _init_db(self, version):
        """Initializes the database from storage including creating tables if necessary.

        Args:
            version: An integer representing the initial version number of the database when newly created
        """
        path = Path(self.path).expanduser().absolute() if self.path != ':memory:' else ':memory:'
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

    @abstractmethod
    def _get_tables_to_create(self):
        """Provides SQL queries to be run when tables are created in the database.

        Returns:
            A list of SQL "CREATE TABLE" commands which will be executed directly on the database
        """
        return []

    @abstractmethod
    def upgrade_db(self, new_version):
        """Verifies the current version against a specified version to perform upgrade modification tasks.

        Args:
            new_version: An integer representing the version that the database should be after maintenance
        """
        pass

    @abstractmethod
    def downgrade_db(self, old_version):
        """Verifies the current version against a specified version to perform downgrade modification tasks.

        This should in theory always reverse the process applied in the upgrade_db() method, unless attempting to
        correct a poorly designed upgrade.

        Args:
            old_version: An integer representing the version that the database should be after maintenance
        """
        pass
