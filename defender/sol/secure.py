"""Secure access to remote and local data."""

import base64
import hashlib
from os import urandom

from sol import sql
from sol.http import ApiServer


class AuthServer(ApiServer):
    """API/HTTP server with basic user authentication from an encrypted database."""

    def _init_authenticator(self):
        return AuthDatabase(self.config.authenticator)


class AuthDatabase(object):
    """User credential authentication database.

    Attributes:
        _dklen: An integer length of the derived key for password hashes.
        _salt_len: An integer length of the salt for password hashes.
        _hash_iter: An integer amount of how many passes the hash should perform.
        _hash_type: A string representing the type of hashing algorithm.
        _auth_table: A table containing credential information.
        _auth_table_cache: A dictionary containing cached table requests.
    """
    KEY_LENGTH = 64
    SALT_LENGTH = 64
    HASH_ITERATIONS = 128 * 1000
    HASH_TYPE = 'sha512'

    def __init__(self, path):
        self._dklen = AuthDatabase.KEY_LENGTH
        self._salt_len = AuthDatabase.SALT_LENGTH
        self._hash_iter = AuthDatabase.HASH_ITERATIONS
        self._hash_type = AuthDatabase.HASH_TYPE
        self._auth_table = AuthTable(path)
        self._auth_table_cache = {}

    def encrypt(self, msg, salt):
        """Encrypts a message using a salt.

        Args:
            msg: A string containing the information to hash.
            salt: A string representing the salt to use for encryption.
        """
        return base64.b64encode(hashlib.pbkdf2_hmac(
            self._hash_type, msg.encode(), salt.encode(), self._hash_iter, self._dklen)).decode('utf-8')

    def generate_salt(self):
        """Generates a salt string."""
        return base64.b64encode(urandom(self._salt_len)).decode('utf-8')

    def add_user(self, username, password):
        """Adds a new user to the backend storage and cache.

        Args:
            username: A string representing the name of the user.
            password: A string containing the password for the user.
        """
        salt = self.generate_salt()
        password = self.encrypt(password, salt)

        user = {
            AuthTable.COLUMN_USER: username,
            AuthTable.COLUMN_PASS: password,
            AuthTable.COLUMN_SALT: salt
        }

        if self._auth_table.add(user) > 0:
            self.cache(user)

    def remove_user(self, username):
        """Removes a user from the backend storage and cache.

        Args:
            username: A string representing the name of the user.

        Returns:
            True if user was removed, False otherwise.
        """
        if self._auth_table.remove(AuthTable.COLUMN_USER + ' = ?', (username,)) > 0:
            self.discard(username)
            return True
        else:
            return False

    def get_user(self, username):
        """Retrieves the information for a user from the backend storage.

        Args:
            username: A string representing the name of the user.

        Returns:
            The first entry found matching the user name, or None.
        """
        entries = self._auth_table.get(('*',), AuthTable.COLUMN_USER + ' = ?', (username,))
        if entries:
            return entries[0]
        else:
            return None

    def get_users(self):
        """Retrieves the information for all users from the backend storage.

        Returns:
            A list of all user entries.
        """
        entries = self._auth_table.get(('*',))
        if entries:
            return entries
        else:
            return []

    def edit_user(self, username, user):
        """Updates the information for a user.

        Args:
            username: A string representing the name of the user to modify.
            user: A dictionary containing the new values for the user.

        Returns:
            An integer amount of entries modified, or -1 if there was an error.
        """
        modified = self._auth_table.update(user, '{} = ?'.format(AuthTable.COLUMN_USER), (username,))
        if modified > 0:
            self.discard(username)
            self.cache(user)
        return modified

    def authenticate(self, username, password):
        """Compares a user's credentials with the information in the database to validate access.

        Args:
            username: A string representing the name of the user.
            password: A string containing the password for the user.

        Returns:
            True if the user passes checks, False if credentials do not match or no user is found.
        """
        if username in self._auth_table_cache:
            entry = self._auth_table_cache[username]
        else:
            entry = self.get_user(username)
            if entry:
                self.cache(entry)
        if entry:
            return entry[AuthTable.COLUMN_PASS] == self.encrypt(password, entry[AuthTable.COLUMN_SALT])
        return False

    def cache(self, user):
        """Stores a user entry in the cache.

        Args:
            user: A dictionary containing the same information from the table for a user.
        """
        self._auth_table_cache[user[AuthTable.COLUMN_USER]] = user

    def discard(self, username):
        """Removes a user entry from the cache.

        Args:
            username: A string representing a username in the cache.
        """
        if username in self._auth_table_cache:
            self._auth_table_cache.pop(username)


class AuthDatabaseHelper(sql.SQLiteHelper):
    """SQLite helper class used to manage creation, upgrades, downgrades, and simplify queries to databases."""

    def upgrade_db(self, new_version):
        if self.database.get_version() < new_version:
            self.database_version = new_version

    def downgrade_db(self, new_version):
        if self.database.get_version() > new_version:
            # Method should be overridden by custom classes
            self.database_version = new_version

    def _get_tables_to_create(self):
        tables = [
            AuthTable
        ]
        return [table.get_table_create_statement() for table in tables]


class AuthTable(sql.SQLiteTable):
    """SQLite table for simple storage of encrypted passwords and salts"""
    TABLE_NAME = 'users'
    COLUMN_USER = 'username'
    COLUMN_PASS = 'password'
    COLUMN_SALT = 'salt'

    def _init_helper(self):
        return AuthDatabaseHelper(self.path)

    def _get_table_name(self):
        return AuthTable.TABLE_NAME

    @staticmethod
    def get_table_create_statement():
        return 'CREATE TABLE {} ({} TEXT PRIMARY KEY UNIQUE, {} TEXT, {} TEXT)'.format(
            AuthTable.TABLE_NAME, AuthTable.COLUMN_USER, AuthTable.COLUMN_PASS, AuthTable.COLUMN_SALT)
