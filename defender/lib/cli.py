"""Shell access for primary application."""

import argparse
import getpass

from defender.lib import shells
from defender.lib.secure import AuthTable


class HostShell(shells.BaseShell):
    """An interactive shell to control frontend and backend services for primary application.

    Attributes:
        apid: An ApiServer which provides access to HTTP frontend and user authentication backend.
        mediad: A MediaServer which provides access to video and audio on the local device.
    """

    def __init__(self, *args):
        super(HostShell, self).__init__('Defender> ', *args)
        self.apid = None
        self.mediad = None

    def _setup_parser(self):
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

        # Exit supbarsers
        parser_exit.add_argument('-f', '--force', help='Force shutdown', action='store_true', default=False)
        return parser

    def _show_banner(self):
        pass

    def _get_cmd_list(self):
        commands = []
        commands.extend(['http logging info', 'http logging debug'])
        commands.extend(['service http start', 'service http stop'])
        commands.extend(['user add', 'user remove', 'user edit', 'user list'])
        return commands

    def exit_root(self, args):
        """Prevents premature exits from program.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: An argsparse namespace package.
        """
        try:
            if not args.force:
                response = input('Exit shell and shutdown all services? Y/n: ')
                if response in ('Y', 'y'):
                    return False
            else:
                return False
        except EOFError:
            print('')
            return False
        except KeyboardInterrupt:
            print('')
        return True

    def http_logging(self, args):
        """Changes the logging level of the HTTP/API service.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: An argsparse namespace package.
        """
        level = args.level
        if level == 'debug':
            print('Warning: Enabling debugging will send additional output to console and logs,'
                  ' and restart the HTTP server.')
            if input('Do you wish to continue? Y/n: ') in ('Y', 'y'):
                self.apid.set_debug(True)
        elif level == 'info':
            print('Warning: disabling debugging will restart the HTTP server.')
            if input('Do you wish to continue? Y/n: ') in ('Y', 'y'):
                self.apid.set_debug(False)
        return True

    def service_http(self, args):
        """Changes the status of the HTTP/API service.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: An argsparse namespace package.
        """
        action = args.action
        if action == 'start':
            self.apid.start()
        elif action == 'stop':
            print('Warning: Stopping the HTTP service will prevent external access to commands,'
                  ' user shell will be required to restart.')
            if input('Do you wish to continue? Y/n: ') in ('Y', 'y'):
                self.apid.shutdown()
        return True

    def user_list(self, args):
        """Lists all users in the database.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: An argsparse namespace package.
        """
        entries = self.apid.server.authenticator.get_users()
        if entries:
            print('User list:\n{}'.format('\n'.join([user['username'] for user in entries])))
        return True

    def user_add(self, args):
        """Adds a new user configuration.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: An argsparse namespace package.
        """
        user = args.username
        if self.apid.server.authenticator.get_user(user):
            print('{} already exists. To modify user, use: user edit {}'.format(user, user))
            return True

        password1 = getpass.getpass('Enter password for {}:'.format(user))
        # TODO add check against simple Passwords
        password2 = getpass.getpass('Re-enter password for {}:'.format(user))

        if password1 != password2:
            print('Passwords do not match')
        else:
            self.apid.server.authenticator.add_user(user, password1)
        return True

    def user_remove(self, args):
        """Removes a user's configuration.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: An argsparse namespace package.
        """
        user = args.username
        entry = self.apid.server.authenticator.get_user(user)
        if not entry:
            print('User {} does not exist'.format(user))
            return True

        print('Do you wish to revoke user {}\'s access?'.format(user))
        if input('Re-enter user\'s name to continue: ') == user:
            if self.apid.server.authenticator.remove_user(user):
                print('User {} access revoked.'.format(user))
            else:
                print('Could not revoke user {} access. Please try again.'.format(user))
        else:
            print('User confirmation did not match. Please try again.')
        return True

    def user_edit(self, args):
        """Edits a user's configuration.

        This function is automatically called by self._execute_cmd() and should not be called manually.

        Args:
            args: An argsparse namespace package.
        """
        user = args.username
        # TODO Allow username change
        entry = self.apid.server.authenticator.get_user(user)
        if not entry:
            print('User {} does not exist'.format(user))
            return True

        password1 = getpass.getpass('Enter password for {}:'.format(user))
        # TODO add check against simple Passwords
        password2 = getpass.getpass('Re-enter password for {}:'.format(user))

        if password1 != password2:
            print('Passwords do not match')
        else:
            entry[AuthTable.COLUMN_SALT] = self.apid.server.authenticator.generate_salt()
            entry[AuthTable.COLUMN_PASS] = self.apid.server.authenticator.encrypt(
                password1, entry[AuthTable.COLUMN_SALT])
            self.apid.server.authenticator.edit_user(user, entry)
        return True
