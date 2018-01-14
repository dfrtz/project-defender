import os
import sqlite3

from pathlib import Path


class SQLiteDatabase(object):
    NO_ENTRY = -1

    def __init__(self, database_name):
        self.database_name = database_name
        self.connection = None

    def create(self):
        sqlite3.connect(self.database_name).close()

    def open(self, flags):
        if not self.is_open():
            self.connection = sqlite3.connect('file:{}?{}'.format(self.database_name, flags), uri=True)

    def is_open(self):
        return not self.connection is None

    def close(self):
        if self.is_open():
            self.connection.close()
            self.connection = None

    def execute(self, statement, values=()):
        cursor = self.connection.cursor()
        cursor.execute(statement, values)
        cursor.close()

    def set_version(self, version):
        cursor = self.connection.cursor()
        cursor.execute('PRAGMA user_version = {}'.format(str(int(version))))
        self.connection.commit()
        cursor.close()

    def get_version(self):
        cursor = self.connection.cursor()
        cursor.execute('PRAGMA user_version')
        row = cursor.fetchone()
        version = row[0]
        cursor.close()

        return int(version)

    def select(self, table_name, columns, selection, selection_args, order_by=None):
        entries = []

        if not self.is_open():
            return entries

        columns_data = ','.join(str(i) for i in columns)
        statement = 'SELECT {} FROM {}'.format(columns_data, table_name)
        if selection is not None and selection != '':
            statement += ' WHERE {}'.format(selection)
        else:
            selection_args = []

        if order_by is not None and order_by != '':
            statement += ' ORDER BY {}'.format(order_by)

        cursor = self.connection.cursor()
        rows = cursor.execute(statement, selection_args).fetchall()
        cursor.close()

        # Expand wildcard into table columns
        if columns == ('*',):
            columns = ()
            for title in cursor.description:
                columns += (title[0],)

        # Expand tuples into dictionaries before returning
        for row in rows:
            entry = {}
            for i in range(0, len(columns)):
                entry[columns[i]] = row[i]
            entries.append(entry)

        return entries

    def insert(self, table_name, entry):
        count = SQLiteDatabase.NO_ENTRY

        if not self.is_open() or entry is None or len(entry) <= 0:
            return count

        value_groups = entry.items()
        columns = self.column_values(value_groups)
        rows = self.qmarks(len(value_groups))
        row_data = self.qmark_values(value_groups, False, True)
        statement = 'INSERT OR IGNORE INTO {} {} VALUES {}'.format(
            table_name, columns, rows)

        cursor = self.connection.cursor()
        cursor.execute(statement, row_data)
        self.connection.commit()
        count = cursor.rowcount
        cursor.close()

        return count

    def update(self, table_name, entry, where_clause, where_args):
        count = SQLiteDatabase.NO_ENTRY

        if not self.is_open() or where_clause == '' or len(where_args) == 0 or entry is None or len(entry) <= 0:
            return count

        value_groups = entry.items()
        columns = self.prepare_columns(value_groups)
        row_data = self.qmark_values(value_groups, False, True) + where_args
        statement = 'UPDATE {} SET {} WHERE {}'.format(
            table_name, columns, where_clause)

        cursor = self.connection.cursor()
        cursor.execute(statement, row_data)
        self.connection.commit()
        count = cursor.rowcount
        cursor.close()

        return count

    def remove(self, table_name, where_clause, where_args):
        count = SQLiteDatabase.NO_ENTRY

        if not self.is_open() or where_clause == '' or len(where_args) == 0:
            return count

        statement = 'DELETE FROM {} WHERE {}'.format(table_name, where_clause)

        cursor = self.connection.cursor()
        cursor.execute(statement, where_args)
        self.connection.commit()
        count = cursor.rowcount
        cursor.close()

        return count

    @staticmethod
    def column_values(value_groups):
        return '({})'.format(','.join(str(key) for key, value in value_groups))

    @staticmethod
    def row_values(value_groups):
        return '({})'.format(','.join(str(value) for key, value in value_groups))

    @staticmethod
    def prepare_columns(value_groups):
        return ','.join(str(key + '= ?') for key, value in value_groups)

    @staticmethod
    def qmarks(count):
        return '({})'.format(','.join('?' for i in range(0, count)))

    @staticmethod
    def qmark_values(value_groups, columns=True, rows=True):
        column_qmarks = ()
        row_qmarks = ()
        for key, value in value_groups:
            if columns:
                column_qmarks += (key,)
            if rows:
                row_qmarks += (value,)

        return column_qmarks + row_qmarks


class SQLiteTable(object):
    TABLE_NAME = 'dummies'
    CREATE_TABLE = 'CREATE TABLE {} (dummy text)'.format(TABLE_NAME)

    def __init__(self, path='dummy.db'):
        self.helper = None
        self.path = path

    def get_helper(self):
        if self.helper is None:
            self.helper = SQLiteHelper(self.path, 1)
        return self.helper

    def get_table_name(self):
        return SQLiteTable.TABLE_NAME

    def get(self, columns, selection=None, selection_args=None, order_by=None):
        database = self.get_helper().get_readable_db()
        entries = database.select(self.get_table_name(), columns, selection, selection_args, order_by)
        database.close()
        return entries

    def add(self, entry):
        database = self.get_helper().get_writable_db()
        count = database.insert(self.get_table_name(), entry)
        database.close()
        return count

    def update(self, entry, where_clause, where_args):
        database = self.get_helper().get_writable_db()
        count = database.update(self.get_table_name(), entry, where_clause, where_args)
        database.close()
        return count

    def remove(self, where_clause, where_args):
        database = self.get_helper().get_writable_db()
        count = database.remove(self.get_table_name(), where_clause, where_args)
        database.close()
        return count


class SQLiteHelper(object):
    def __init__(self, database_name, database_version):
        self.database_name = database_name
        self.database = None

        self._create(database_version)
        self.open('mode=rw')
        self.upgrade_db(database_version)
        self.downgrade_db(database_version)
        self.close()

    def open(self, flags='mode=rw'):
        self.database.open(flags)

    def close(self):
        self.database.close()

    def _create(self, version):
        path = Path(self.database_name).expanduser().absolute()
        exists = path.is_file()

        # DB must be created after checking path to prevent accidental creation
        self.database = SQLiteDatabase(path)

        if not exists:
            parent = Path(path.parent)
            if not parent.is_dir():
                parent.mkdir(parents=True, exist_ok=True)
            self.database.create()
            self.open()
            self.database.set_version(version)
            for table in self.get_tables():
                self.database.execute(table)
            self.close()

    def get_tables(self):
        return []

    def upgrade_db(self, new_version):
        if self.database.get_version() < new_version:
            # Method should be overridden by custom classes
            self.database_version = new_version

    def downgrade_db(self, new_version):
        if self.database.get_version() > new_version:
            # Method should be overridden by custom classes
            self.database_version = new_version

    def get_writable_db(self):
        self.open('more=rw')
        return self.database

    def get_readable_db(self):
        self.open('mode=ro')
        return self.database
