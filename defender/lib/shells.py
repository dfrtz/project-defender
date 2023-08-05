"""Interactive shells for isolated user program access."""

import abc
import argparse
import readline

from typing import List
from typing import Union


class ShellCompleter(list):
    """A command completion container which validates user input against the stored contents to find matches.

    Attributes:
        matches: A list of strings that begin with a comparison string.
    """

    def __init__(self) -> None:
        """Initialize a basic complete with no possible matches."""
        super(ShellCompleter, self).__init__()
        self.matches = []

    def complete(self, text: str, state: int) -> Union[str, None]:
        """Compares the current input buffer against all stored strings to display valid completion options.

        This method should be used in conjunction with readline.set_completer(func) to enable autocompletion.

        Args:
            text: Value to compare to all values in this completer.
            state: The state'th item in the matched items
        """
        if not state:
            if text:
                self.matches = [string for string in self if string.startswith(text)]
            else:
                self.matches = self[:]
        result = None
        try:
            result = self.matches[state]
        except IndexError:
            # Do nothing, there was no match.
            pass
        return result


class BaseShell(object, metaclass=abc.ABCMeta):
    """Base level interactive shell to read, parse, and execute user commands.

    Attributes:
        _original_completer: A completer function that is active when first loading the shell and restored when closing.
        _completer: A completer function that is active during the duration of the shell.
        _parser: An argument parser that will be used to process commands.
        _prompt: A string that will be displayed whenever the user can run a command.
    """

    def __init__(self, prompt: str = 'Shell> ') -> None:
        """Set up a basic interactive shell."""
        self._original_completer = readline.get_completer()
        self._completer = self._setup_completer()
        self._parser = self._setup_parser()
        self._prompt = prompt
        self._show_banner()
        readline.set_completer(self._completer.complete)
        readline.parse_and_bind('tab: complete')
        readline.set_completer_delims('')

    def _execute_cmd(self, cmd: str) -> bool:
        """Services the root request for a command by calling child functions based on the root argument and command type.

        Examples of prompt translation:
            Prompt> exit = exit(args)
            Prompt> edit user = edit_user(args)
            Prompt> edit machine = edit_machine(args)
            Prompt> stop service margaritabar = stop_service(args)

        Args:
            cmd: A user command to be executed.

        Returns:
            True if command was consumed and additional input is allowed, False no further input is accepted.
        """
        try:
            args = self._parser.parse_args(cmd.split())
        except SystemExit:
            return True

        result = True
        method_suffix = args.branch.lower() if hasattr(args, 'branch') else 'root'
        method_name = f'{args.root.lower()}_{method_suffix}'
        if hasattr(self, method_name):
            method = getattr(self, method_name)
            result = method(args)
        else:
            if cmd.startswith('exit'):
                if self._original_completer is not None:
                    readline.set_completer(self._original_completer)
                result = False
            elif cmd.startswith('help'):
                if self._parser:
                    self._parser.print_help()
        return result

    @abc.abstractmethod
    def _get_cmd_list(self) -> List[str]:
        """Provides a list of available commands.

        Returns:
            An iterable list of strings representing fully typed commands.
        """

    def _setup_completer(self) -> ShellCompleter:
        """Creates a new command line completer.

        Returns:
            A Completer to help users auto-complete commands.
        """
        completer = ShellCompleter()
        completer.extend(['exit', 'help'])
        completer.extend(self._get_cmd_list())
        return completer

    @abc.abstractmethod
    def _setup_parser(self) -> argparse.ArgumentParser:
        """Creates a new argument parser which can be fed text based commands.

        Returns:
            An ArgumentParser to process strings into an args package, with the first argument stored as 'parser.root',
            and the second stored as 'parser.branch'.
        """

    def _show_banner(self) -> None:
        """Displays a message when the shell is launched."""
        print('Entering subconsole.')

    def prompt_user(self) -> bool:
        """Prompts for and services a user command by passing along if it is valid, or discarding if it is invalid.

        Returns:
            True if command was consumed and additional input is allowed, False if no further input will be accepted.
        """
        while True:
            try:
                cmd = input(self._prompt).strip()
            except EOFError:
                print()
                result = False
                break
            except KeyboardInterrupt:
                print()
                continue
            if cmd != '':
                result = self._execute_cmd(cmd)
                break
        return result
