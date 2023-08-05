"""Secure access to remote and local data."""

import base64
import hashlib
import os
from typing import List
from typing import Union

from defender.lib import sql
from defender.lib.http import ApiServer


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

    key_length = 64
    salt_length = 64
    hash_iterations = 128 * 1000
    hash_type = "sha512"

    def __init__(self, path: str) -> None:
        """Setup the database with all required encryption values."""
        self._dklen = AuthDatabase.key_length
        self._salt_len = AuthDatabase.salt_length
        self._hash_iter = AuthDatabase.hash_iterations
        self._hash_type = AuthDatabase.hash_type
        self._auth_table = AuthTable(path)
        self._auth_table_cache = {}

    def add_user(self, username: str, password: str) -> None:
        """Adds a new user to the backend storage and cache.

        Args:
            username: The name of the user to add.
            password: The password for the user.
        """
        salt = self.generate_salt()
        password = self.encrypt(password, salt)

        user = {AuthTable.column_user: username, AuthTable.column_pass: password, AuthTable.column_salt: salt}

        if self._auth_table.add(user) > 0:
            self.cache(user)

    def authenticate(self, username: str, password: str) -> bool:
        """Compares a user's credentials with the information in the database to validate access.

        Args:
            username: The name of the user to verify.
            password: The expected password for the user.

        Returns:
            True if the user passes checks, False if credentials do not match or no user is found.
        """
        if username in self._auth_table_cache:
            entry = self._auth_table_cache[username]
        else:
            entry = self.get_user(username)
            if entry:
                self.cache(entry)
        authenticated = False
        if entry:
            authenticated = entry[AuthTable.column_pass] == self.encrypt(password, entry[AuthTable.column_salt])
        return authenticated

    def cache(self, user: dict) -> None:
        """Stores a user entry in the cache.

        Args:
            user: The information from the table for a user.
        """
        self._auth_table_cache[user[AuthTable.column_user]] = user

    def discard(self, username: str) -> None:
        """Removes a user entry from the cache.

        Args:
            username: A username in the cache.
        """
        if username in self._auth_table_cache:
            self._auth_table_cache.pop(username)

    def edit_user(self, username: str, user: dict) -> int:
        """Updates the information for a user.

        Args:
            username: The name of the user to modify.
            user: A dictionary containing the new values for the user.

        Returns:
            The amount of entries modified, or -1 if there was an error.
        """
        modified = self._auth_table.update(user, f"{AuthTable.column_user} = ?", (username,))
        if modified > 0:
            self.discard(username)
            self.cache(user)
        return modified

    def encrypt(self, msg: str, salt: str) -> str:
        """Encrypts a message using a salt.

        Args:
            msg: The information to encrypt.
            salt: The salt to use for encryption.

        Returns:
            The encrypted message.
        """
        hmac = hashlib.pbkdf2_hmac(self._hash_type, msg.encode(), salt.encode(), self._hash_iter, self._dklen)
        msg = base64.b64encode(hmac).decode("utf-8")
        return msg

    def generate_salt(self) -> str:
        """Generates a salt string.

        Returns:
            A random salt.
        """
        salt = base64.b64encode(os.urandom(self._salt_len)).decode("utf-8")
        return salt

    def get_user(self, username: str) -> Union[dict, None]:
        """Retrieves the information for a user from the backend storage.

        Args:
            username: The name of the user to retrieve.

        Returns:
            The first entry found matching the user name, or None.
        """
        entries = self._auth_table.get(("*",), f"{AuthTable.column_user} = ?", (username,))
        if entries:
            user = entries[0]
        else:
            user = None
        return user

    def get_users(self) -> List[dict]:
        """Retrieves the information for all users from the backend storage.

        Returns:
            All user entries.
        """
        entries = self._auth_table.get(("*",))
        return entries

    def remove_user(self, username: str) -> bool:
        """Removes a user from the backend storage and cache.

        Args:
            username: The name of the user to remove.

        Returns:
            True if user was removed, False otherwise.
        """
        removed = False
        if self._auth_table.remove(f"{AuthTable.column_user} = ?", (username,)) > 0:
            self.discard(username)
            removed = True
        return removed


class AuthDatabaseHelper(sql.SQLiteHelper):
    """SQLite helper class used to manage creation, upgrades, downgrades, and simplify queries to databases."""

    def _get_tables_to_create(self) -> List[str]:
        """Provides SQL queries to be run when tables are created in the database.

        Returns:
            A list of SQL "CREATE TABLE" commands which will be executed directly on the database.
        """
        tables = [AuthTable]
        commands = [table.get_table_create_statement() for table in tables]
        return commands

    def downgrade_db(self, new_version: int) -> None:
        """Verifies the current version against a specified version to perform downgrade modification tasks.

        This should in theory always reverse the process applied in the upgrade_db() method, unless attempting to
        correct a poorly designed upgrade.

        Args:
            new_version: The version that the database should be after maintenance.
        """
        if self.database.get_version() > new_version:
            # Method should be overridden by custom classes
            self.database_version = new_version

    def upgrade_db(self, new_version: int) -> None:
        """Verifies the current version against a specified version to perform upgrade modification tasks.

        Args:
            new_version: The version that the database should be after maintenance.
        """
        if self.database.get_version() < new_version:
            self.database_version = new_version


class AuthServer(ApiServer):
    """API/HTTP server with basic user authentication from an encrypted database."""

    def _init_authenticator(self) -> AuthDatabase:
        return AuthDatabase(self.config.authenticator)


class AuthTable(sql.SQLiteTable):
    """SQLite table for simple storage of encrypted passwords and salts."""

    table_name = "users"
    column_user = "username"
    column_pass = "password"
    column_salt = "salt"

    def _get_table_name(self) -> str:
        """Creates a string for the table to use with all SQL queries.

        This method should only be called once during initialization of the object and should never be called manually.

        Returns:
            A string representing the name of this table in a database which will be used for all queries.
        """
        return AuthTable.table_name

    def _init_helper(self) -> AuthDatabaseHelper:
        """Creates a database helper to manage all connectivity to storage during queries.

        This method should only be called once during initialization of the object and should never be called manually.

        Returns:
            A helper which will be used to manage all database access requests.
        """
        helper = AuthDatabaseHelper(self.path)
        return helper

    @staticmethod
    def get_table_create_statement() -> str:
        """Creates a string to be used when the table is initially created on the storage.

        Returns:
            A SQL string that can be executed on a database to create the table.
        """
        command = f"CREATE TABLE {AuthTable.table_name} ({AuthTable.column_user} TEXT PRIMARY KEY UNIQUE, {AuthTable.column_pass} TEXT, {AuthTable.column_salt} TEXT)"
        return command
