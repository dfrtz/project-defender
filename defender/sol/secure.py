import base64
import hashlib
import os

from sol import sql
from sol.http import ApiServer
from sol.http import ServerConfig


class AuthServer(ApiServer):
    def authenticate(self, user, password):
        return self.config.db.authenticate(user, password)


class AuthServerConfig(ServerConfig):
    def __init__(self):
        super(AuthServerConfig, self).__init__()
        self.thread_handler = AuthServer


class AuthDatabase(object):
    SALT_LENGTH = 64
    HASH_ITERATIONS = 128 * 1000

    def __init__(self, path):
        self._salt_length = AuthDatabase.SALT_LENGTH
        self._hash_iterations = AuthDatabase.HASH_ITERATIONS
        self._authentication_table = AuthenticationTable(path)
        self._authentication_table_cache = {}

    def encrypt(self, msg, salt):
        return base64.b64encode(
            hashlib.pbkdf2_hmac('sha256', msg.encode(), salt.encode(), self._hash_iterations)).decode('utf-8')

    def add_user(self, username, password, encrypted=False):
        salt = base64.b64encode(os.urandom(self._salt_length)).decode('utf-8')

        if not encrypted:
            password = self.encrypt(password, salt)

        user = {
            AuthenticationTable.COLUMN_USER: username,
            AuthenticationTable.COLUMN_PASS: password,
            AuthenticationTable.COLUMN_SALT: salt
        }

        if self._authentication_table.add(user) > 0:
            self.cache(user)

    def remove_user(self, username):
        if self._authentication_table.remove(AuthenticationTable.COLUMN_USER + ' = ?', (username,)) > 0:
            self.discard(username)
            return True
        else:
            return False

    def get_user(self, username):
        entries = self._authentication_table.get(('*',), AuthenticationTable.COLUMN_USER + ' = ?', (username,))
        if entries:
            return entries[0]
        else:
            return None

    def get_users(self):
        entries = self._authentication_table.get(('*',))
        if entries:
            return entries[0]
        else:
            return None

    def edit_user(self, username, user):
        modified = self._authentication_table.update(user, AuthenticationTable.COLUMN_USER + ' = ?', (username,))
        if modified > 0:
            self.discard(username)
            self.cache(user)

        return modified

    def authenticate(self, username, password, encrypted=False):
        if username in self._authentication_table_cache:
            entry = self._authentication_table_cache[username]
        else:
            entry = self.get_user(username)

            if entry:
                self.cache(entry)

        if entry:
            if not encrypted:
                password = self.encrypt(password, entry[AuthenticationTable.COLUMN_SALT])

            return entry[AuthenticationTable.COLUMN_PASS] == password

        return False

    def cache(self, user):
        username = user[AuthenticationTable.COLUMN_USER]
        if username not in self._authentication_table_cache:
            self._authentication_table_cache[username] = user

    def discard(self, username):
        if username in self._authentication_table_cache:
            self._authentication_table_cache.pop(username)


class AuthDatabaseHelper(sql.SQLiteHelper):
    def __init__(self, path):
        super(AuthDatabaseHelper, self).__init__(path, database_version=1)

    def get_tables(self):
        return [
            AuthenticationTable.CREATE_TABLE
        ]


class AuthenticationTable(sql.SQLiteTable):
    TABLE_NAME = 'users'

    COLUMN_USER = 'username'
    COLUMN_PASS = 'password'
    COLUMN_SALT = 'salt'

    CREATE_TABLE = 'CREATE TABLE {} ({} text PRIMARY KEY UNIQUE, {} text, {} text)'.format(
        TABLE_NAME, COLUMN_USER, COLUMN_PASS, COLUMN_SALT)

    def get_helper(self):
        if self.helper is None:
            self.helper = AuthDatabaseHelper(self.path)
        return self.helper

    def get_table_name(self):
        return AuthenticationTable.TABLE_NAME
