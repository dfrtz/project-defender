import argparse
import readline


class BaseShell(object):
    def __init__(self, prompt='Shell> ', *args):
        self._original_completer = readline.get_completer()
        self._commands = ['exit', 'help']
        self.setup_completer([])

        self.prompt = prompt
        self.banner = None

        self.parser = argparse.ArgumentParser(prog='', description='Python subconsole')
        self.parser.add_argument('help', help='Display help', action='store')
        self.parser.add_argument('exit', help='Exit subconsole', action='store')

    def setup_completer(self, commands):
        self._completer = ShellCompleter()
        self._completer.extend(self._commands)
        self._completer.extend(commands)

        readline.set_completer(self._completer.complete)
        readline.parse_and_bind("tab: complete")
        readline.set_completer_delims('')

    def run_command(self, prompt):
        while True:
            try:
                cmd = input(prompt).strip()
            except EOFError:
                print()
                return False
            except KeyboardInterrupt:
                print()
                continue

            if cmd == '':
                return True
            else:
                return self.execute_cmd(cmd)

    def execute_cmd(self, cmd):
        if cmd.startswith('exit'):
            if self._original_completer is not None:
                readline.set_completer(self._original_completer)
            return False
        elif cmd.startswith('help'):
            if self.parser:
                self.parser.print_help()
        return True


class ShellCompleter(list):
    def complete(self, text, state):
        for cmd in self:
            text = readline.get_line_buffer()
            if cmd.startswith(text):
                if not state:
                    return cmd
                else:
                    state -= 1
