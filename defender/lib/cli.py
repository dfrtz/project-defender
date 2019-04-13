"""Shell access for primary application."""

import argparse
import getpass

from defender.lib import shells
from defender.lib.secure import AuthTable


class HostShell(shells.BaseShell):
    """An interactive shell class to control frontend and backend services for primary application.

    All parser commands are defined in this class and automatically called depending on user input.
    For example, if 'http logging' is entered by user, then http_logging(args) is called.

    Attributes:
        apid: An ApiServer which provides access to HTTP frontend and user authentication backend.
        mediad: A MediaServer which provides access to video and audio on the local device.
    """

    def __init__(self) -> None:
        """Initializes the base shell with prefix and null daemons."""
        super(HostShell, self).__init__('Defender> ')
        self.apid = None
        self.mediad = None

    def _get_cmd_list(self) -> list:
        """Creates a list of all commands that should autocomplete."""
        commands = [
            *['http logging info', 'http logging debug'],
            *['service http start', 'service http stop'],
            *['user add', 'user remove', 'user edit', 'user list']
        ]
        return commands

    def _setup_parser(self) -> argparse.ArgumentParser:
        """Setup all subcommand parsers accessible to the end user."""
        parser = argparse.ArgumentParser(prog='', description='Defense Monitoring System')

        # First level parsers
        parsers = parser.add_subparsers(title='Commands', dest='root')
        parsers.required = True
        parser_help = parsers.add_parser('help', help='List commands and functions')
        parser_http = parsers.add_parser('http', help='Modify HTTP subsystems')
        parser_service = parsers.add_parser('service', help='Control services')
        parser_user = parsers.add_parser('user', help='Modify user accounts')
        parser_exit = parsers.add_parser('exit', help='Exit program')

        # HTTP subparsers
        subparsers_http = parser_http.add_subparsers(title='Subsystems', dest='branch')
        subparsers_http.required = True
        subparser_http_debug = subparsers_http.add_parser('logging', help='HTTP/API logging configuration')
        subparser_http_debug.add_argument('level', help='Logging level', action='store', choices=['info', 'debug'])

        # Service subparsers
        subparsers_service = parser_service.add_subparsers(title='Services', dest='branch')
        subparsers_service.required = True
        subparser_service_http = subparsers_service.add_parser('http', help='HTTP/API service')
        subparser_service_http.add_argument('action', help='Service Action', action='store', choices=['start', 'stop'])

        # User subparsers
        subparsers_user = parser_user.add_subparsers(title='Actions', dest='branch')
        subparsers_user.required = True
        subparser_user_list = subparsers_user.add_parser('list', help='List users in database')
        subparser_user_add = subparsers_user.add_parser('add', help='Add new user account')
        subparser_user_add.add_argument('username', help='User name', action='store')
        subparser_user_remove = subparsers_user.add_parser('remove', help='Remove existing user account')
        subparser_user_remove.add_argument('username', help='User name', action='store')
        subparser_user_edit = subparsers_user.add_parser('edit', help='Edit existing user account')
        subparser_user_edit.add_argument('username', help='User name', action='store')
        subparser_user_edit.add_argument('-p', '--password', help='Prompts for new user credentials.',
                                         action='store_true')

        # Exit subparsers
        parser_exit.add_argument('-f', '--force', help='Force shutdown', action='store_true', default=False)
        return parser

    def _show_banner(self) -> None:
        """Do not show any banner to the user."""

    def exit_root(self, args: argparse.Namespace) -> bool:
        """Prevents premature exits from program.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: User arguments from CLI.

        Returns:
            True if the command was handled and should continue looping. False if exit is requested.
        """
        cmd_handled = True
        try:
            if not args.force:
                response = input('Exit shell and shutdown all services? Y/n: ')
                if response.lower() == 'y':
                    cmd_handled = False
            else:
                cmd_handled = False
        except EOFError:
            # CTRL+D intercept.
            print('')
            cmd_handled = False
        except KeyboardInterrupt:
            # CTRL+C intercept.
            print('')
        return cmd_handled

    def http_logging(self, args: argparse.Namespace) -> bool:
        """Changes the logging level of the HTTP/API service.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: User arguments from CLI.

        Returns:
            True to indicate the command was handled.
        """
        cmd_handled = True
        level = args.level
        if level == 'debug':
            print('Warning: Enabling debugging will send additional output to console and logs, and restart the HTTP server.')
            if input('Do you wish to continue? Y/n: ').lower() == 'y':
                self.apid.set_debug(True)
        elif level == 'info':
            print('Warning: disabling debugging will restart the HTTP server.')
            if input('Do you wish to continue? Y/n: ').lower() == 'y':
                self.apid.set_debug(False)
        return cmd_handled

    def service_http(self, args: argparse.Namespace) -> bool:
        """Changes the status of the HTTP/API service.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: User arguments from CLI.

        Returns:
            True to indicate the command was handled.
        """
        cmd_handled = True
        action = args.action
        if action == 'start':
            self.apid.start()
        elif action == 'stop':
            print('Warning: Stopping the HTTP service will prevent external access to commands, user shell will be required to restart.')
            if input('Do you wish to continue? Y/n: ').lower() == 'y':
                self.apid.shutdown()
        return cmd_handled

    def user_add(self, args: argparse.Namespace) -> bool:
        """Adds a new user configuration.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: User arguments from CLI.

        Returns:
            True to indicate the command was handled.
        """
        cmd_handled = True
        user = args.username
        if self.apid.server.authenticator.get_user(user):
            print(f'{user} already exists. To modify user, use: user edit {user}')
        else:
            password1 = getpass.getpass(f'Enter password for {user}:')
            # TODO add check against simple Passwords
            password2 = getpass.getpass(f'Re-enter password for {user}:')

            if password1 != password2:
                print('Passwords do not match')
            else:
                self.apid.server.authenticator.add_user(user, password1)
        return cmd_handled

    def user_edit(self, args: argparse.Namespace) -> bool:
        """Edits a user's configuration.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: User arguments from CLI.

        Returns:
            True to indicate the command was handled.
        """
        cmd_handled = True
        user = args.username
        # TODO Allow username change
        entry = self.apid.server.authenticator.get_user(user)
        if not entry:
            print(f'User {user} does not exist')
        else:
            password1 = getpass.getpass(f'Enter password for {user}:')
            # TODO add check against simple Passwords
            password2 = getpass.getpass(f'Re-enter password for {user}:')

            if password1 != password2:
                print('Passwords do not match')
            else:
                entry[AuthTable.column_salt] = self.apid.server.authenticator.generate_salt()
                entry[AuthTable.column_pass] = self.apid.server.authenticator.encrypt(
                    password1, entry[AuthTable.column_salt])
                self.apid.server.authenticator.edit_user(user, entry)
        return cmd_handled

    def user_list(self, args: argparse.Namespace) -> bool:
        """Lists all users in the database.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: User arguments from CLI.

        Returns:
            True to indicate the command was handled.
        """
        cmd_handled = True
        entries = self.apid.server.authenticator.get_users()
        if entries:
            users = '\n'.join([user['username'] for user in entries])
            print(f'User list:\n{users}')
        return cmd_handled

    def user_remove(self, args: argparse.Namespace) -> bool:
        """Removes a user's configuration.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: User arguments from CLI.

        Returns:
            True to indicate the command was handled.
        """
        cmd_handled = True
        user = args.username
        entry = self.apid.server.authenticator.get_user(user)
        if not entry:
            print(f'User {user} does not exist')
        else:
            print(f'Do you wish to revoke user {user}\'s access?')
            if input('Re-enter user\'s name to continue: ') == user:
                if self.apid.server.authenticator.remove_user(user):
                    print(f'User {user} access revoked.')
                else:
                    print(f'Could not revoke user {user} access. Please try again.')
            else:
                print('User confirmation did not match. Please try again.')
        return cmd_handled
