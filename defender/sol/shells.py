"""Interactive shells for isolated user program access."""

import readline
from abc import ABC, abstractmethod


class BaseShell(ABC):
    """Base level interactive shell to read, parse, and execute user commands.

    Attributes:
        _original_completer: A completer function that is active when first loading the shell and restored when closing.
        _completer: A completer function that is active during the duration of the shell.
        _parser: An argument parser that will be used to process commands.
        _prompt: A string that will be displayed whenever the user can run a command.
    """

    def __init__(self, prompt='Shell> ', *args):
        self._original_completer = readline.get_completer()
        self._completer = self._setup_completer()
        self._parser = self._setup_parser()
        self._prompt = prompt
        self._show_banner()

        readline.set_completer(self._completer.complete)
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims('')

    def _setup_completer(self):
        """Creates a new command line completer.

        Returns:
            A ShellCompleter to help users auto-complete commands.
        """
        completer = ShellCompleter()
        completer.extend(['exit', 'help'])
        completer.extend(self._get_cmd_list())
        return completer

    @abstractmethod
    def _get_cmd_list(self):
        """Provides a list of available commands.

        Returns:
            An iterable list of strings representing fully typed commands.
        """
        return []

    @abstractmethod
    def _setup_parser(self):
        """Creates a new argument parser which can be fed text based commands.

        Returns:
            An ArgumentParser to process strings into an args package, with the first argument stored as 'parser.root',
            and the second stored as 'parser.branch'.
        """
        pass

    def _show_banner(self):
        """Displays a message when the shell is launched."""
        print('Entering subconsole.')

    def _execute_cmd(self, cmd):
        """Services the root request for a command by calling child functions based on the root argument and command type.

        Examples of prompt translation:
            Prompt> exit = exit(args)
            Prompt> edit user = edit_user(args)
            Prompt> edit machine = edit_machine(args)
            Prompt> stop service margaritabar = stop_service(args)

        Args:
            cmd: A string representing a user command to be executed.

        Returns:
            True if command was consumed and additional input is allowed, False no further input is accepted.
        """
        try:
            args = self._parser.parse_args(cmd.split())
        except SystemExit:
            return True

        method_name = '{}_{}'.format(args.root.lower(), args.branch.lower() if hasattr(args, 'branch') else 'root')
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            return method(args)
        else:
            if cmd.startswith('exit'):
                if self._original_completer is not None:
                    readline.set_completer(self._original_completer)
                return False
            elif cmd.startswith('help'):
                if self._parser:
                    self._parser.print_help()
            return True

    def prompt_user(self):
        """Prompts for and services a user command by passing along if it is valid, or discarding if it is invalid.

        Returns:
            True if command was consumed and additional input is allowed, False if no further input will be accepted.
        """
        while True:
            try:
                cmd = input(self._prompt).strip()
            except EOFError:
                print()
                return False
            except KeyboardInterrupt:
                print()
                continue

            if cmd == '':
                return True
            else:
                return self._execute_cmd(cmd)


class ShellCompleter(list):
    """A command completion container which validates user input against the stored contents to find matches.

    Attributes:
        matches: A list of strings that begin with a comparison string.
    """

    def __init__(self):
        super(ShellCompleter, self).__init__()
        self.matches = []

    def complete(self, text, state):
        """Compares the current input buffer against all stored strings to display valid completion options.

        This method should be used in conjunction with readline.set_completer(func) to enable autocompletion.

        Args:
            text: A string which will be compared to all values in this completer.
            state: An integer representing the state'th item in the matched items
        """
        if not state:
            if text:
                self.matches = [string for string in self if string.startswith(text)]
            else:
                self.matches = self[:]

        try:
            return self.matches[state]
        except IndexError:
            pass
        return None
