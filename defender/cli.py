import argparse
import getpass
import json

from sol import shells, http
from sol.secure import AuthenticationTable


class HostShell(shells.BaseShell):
    def __init__(self, *args):
        super(HostShell, self).__init__('Defender> ', *args)

        self._commands = []
        self._config = http.ServerConfig()
        self._authdb = None
        self._httpd = None

        self.setup_parsers()
        self.setup_completer(self._commands)

    def setup_parsers(self):
        self.parser = argparse.ArgumentParser(prog='', description='Home Defense Monitoring System')

        # First level parsers
        parsers = self.parser.add_subparsers(title='Commands', dest='parser')
        parsers.required = True

        parser_help = parsers.add_parser('help', help='List commands and functions')
        parser_http = parsers.add_parser('http', help='Modify HTTP subsystems')
        parser_service = parsers.add_parser('service', help='Control services')
        parser_user = parsers.add_parser('user', help='Modify user accounts')
        parser_exit = parsers.add_parser('exit', help='Exit program')

        # HTTP subparsers
        subparsers_http = parser_http.add_subparsers(title='Subsystems', dest='subsystem')
        subparsers_http.required = True

        subparser_http_debug = subparsers_http.add_parser('logging', help='HTTP/API logging configuration')
        subparser_http_debug.add_argument('level', help='Logging level', action='store', choices=['info', 'debug'])
        self._commands.extend(['http logging info', 'http logging debug'])

        # Service subparsers
        subparsers_service = parser_service.add_subparsers(title='Services', dest='service')
        subparsers_service.required = True

        subparser_service_http = subparsers_service.add_parser('http', help='HTTP/API service')
        subparser_service_http.add_argument('action', help='Service Action', action='store', choices=['start', 'stop'])
        self._commands.extend(['service http start', 'service http stop'])

        # User subparsers
        subparsers_user = parser_user.add_subparsers(title='Actions', dest='action')
        subparsers_user.required = True

        subparser_user_add = subparsers_user.add_parser('add', help='Add new user account')
        subparser_user_add.add_argument('username', help='User name', action='store')
        subparser_user_remove = subparsers_user.add_parser('remove', help='Remove existing user account')
        subparser_user_remove.add_argument('username', help='User name', action='store')
        subparser_user_edit = subparsers_user.add_parser('edit', help='Edit existing user account')
        subparser_user_edit.add_argument('username', help='User name', action='store')
        subparser_user_edit.add_argument('-p', '--password', help='Prompts for new user credentials.',
                                         action='store_true')
        subparser_user_list = subparsers_user.add_parser('list', help='List users in database')
        self._commands.extend(['user add', 'user remove', 'user edit', 'user list'])

        # Exit supbarsers
        parser_exit.add_argument('-f', '--force', help='Force shutdown', action='store_true', default=False)
        self._commands.extend(['exit'])

    def set_authdb(self, authdb):
        self._authdb = authdb

    def set_httpd(self, httpd):
        self._httpd = httpd

    def set_config(self, config):
        self._config = config

    def execute_cmd(self, cmd):
        try:
            args = self.parser.parse_args(cmd.split())
        except SystemExit:
            return True

        # TODO Move hash to AuthDatabase and implement salting

        command = args.parser
        if command == 'exit':
            try:
                if not args.force:
                    response = input('Exit shell and shutdown all services? Y/n: ')
                    if response == 'Y' or response == 'y':
                        return False
                else:
                    return False
            except EOFError:
                print('')
                return False
            except KeyboardInterrupt:
                print('')
        elif command == 'http':
            level = args.level
            if level == 'debug':
                response = input(
                    'Warning: Enabling debugging will send additional output to console and logs, and restart the HTTP server.\n'
                    + 'Do you wish to continue? Y/n: ')
                if response == 'Y' or response == 'y':
                    self._httpd.set_debug(True)
            elif level == 'info':
                response = input('Warning: disabling debugging will restart the HTTP server.\n'
                                 + 'Do you wish to continue? Y/n: ')
                if response == 'Y' or response == 'y':
                    self._httpd.set_debug(False)
        elif command == 'service':
            service = args.service

            if service == 'http':
                action = args.action

                if action == 'start':
                    self._httpd.start()
                elif action == 'stop':
                    response = input(
                        'Warning: Stopping the HTTP service will prevent external access to commands, user shell will be required to restart.\n'
                        + 'Do you wish to continue? Y/n: ')
                    if response == 'Y' or response == 'y':
                        self._httpd.shutdown()
        elif command == 'user':
            action = args.action
            user = ''
            if action != 'list':
                user = args.username

            if action == 'add':
                if self._authdb.get_user(user):
                    print('{} already exists. To modify user, use: user edit {}'.format(user, user))
                    return True

                password1 = getpass.getpass('Enter password for {}:'.format(user))
                # TODO add check against simple Passwords
                password2 = getpass.getpass('Re-enter password for {}:'.format(user))

                if password1 != password2:
                    print('Passwords do not match')
                else:
                    self._authdb.add_user(user, password1)
            elif action == 'remove':
                entry = self._authdb.get_user(user)
                if not entry:
                    print('User {} does not exist'.format(user))
                    return True

                response = input('Do you wish to revoke user {}\'s access?.\n'.format(user)
                                 + 'Re-enter user\'s name to continue: ')
                if response == user:
                    if self._authdb.remove_user(user):
                        print('User {} access revoked.'.format(user))
                    else:
                        print('Could not revoke user {} access. Please try again.'.format(user))
                else:
                    print('User confirmation did not match. Please try again.')
            elif action == 'edit':
                # TODO Allow username change
                entry = self._authdb.get_user(user)
                if not entry:
                    print('User {} does not exist'.format(user))
                    return True

                password1 = getpass.getpass('Enter password for {}:'.format(user))
                # TODO add check against simple Passwords
                password2 = getpass.getpass('Re-enter password for {}:'.format(user))

                if password1 != password2:
                    print('Passwords do not match')
                else:
                    entry[AuthenticationTable.COLUMN_PASS] = self._authdb.encrypt(password1, entry[
                        AuthenticationTable.COLUMN_SALT])
                    self._authdb.edit_user(user, entry)
            elif action == 'list':
                # TODO Allow username change
                entries = self._authdb.get_users()
                if entries:
                    print('User list:\n{}'.format(json.dumps(entries)))
                    return True
        else:
            return super(HostShell, self).execute_cmd(command)

        return True
