# """
# An RPN Calculator
# """

import sublime
import sublime_plugin
import math
from . import globals

__author__ = 'Brian Hunter'
__email__ = 'brian.p.hunter@gmail.com'
__version__ = '0.1'


########################################################################################
# Globals

########################################################################################
class InsufficientStackDepth(Exception):
    "Raised when a command requires more values than are on the stack."

    def __init__(self, required):
        self.required = required


########################################################################################
class RpnCommand(sublime_plugin.WindowCommand):
    "Launches the rpn view"

    #--------------------------------------------
    def run(self):
        self.opanel = None
        for aview in self.window.views():
            if aview.name() == globals.RPN_WINDOW_NAME:
                self.opanel = aview
                break

        if self.opanel is None:
            self.opanel = self.window.new_file()
            self.opanel.set_name(globals.RPN_WINDOW_NAME)
            self.opanel.set_scratch(True)

        self.window.focus_view(self.opanel)

########################################################################################
class RPNEvent(sublime_plugin.EventListener):
    "Handles all the work for RPN"

    def __init__(self):
        super(RPNEvent, self).__init__()

        self.opanel = None
        self.done = False
        self.prev_stack, self.stack = [], []

        always_legal_cmds = {
            'U': self.undo,
            'C': self.clear_stack,
            'S': self.swap_stack,
            '?': self.help,
            ':': self.change_mode,
        }

        basic_cmds = {
            '+': self.add,
            '-': self.subtract,
            '*': self.multiply,
            '/': self.divide,
            '%': self.modulo,
        }

        programmer_cmds = {
            '|': self.or_func,
            '&': self.and_func,
            '~': self.not_func,
            '^': self.xor,
            '<': self.shift_left,
            '>': self.shift_right,
        }

        scientific_cmds = {
            '^': self.exponent,
        }

        self.mode_commands = {
            'D': self.decimal,
            'H': self.hexadecimal,
            'O': self.octal,
            'B': self.binary,
            'b': self.mode_basic,
            'P': self.mode_programmer,
            'S': self.mode_scientific,
            ':': self.quit_change_mode
        }

        self.all_commands = always_legal_cmds.copy()
        self.all_commands.update(basic_cmds)
        self.all_commands.update(programmer_cmds)
        self.all_commands.update(scientific_cmds)

        self.basic_commands = {}
        self.basic_commands.update(always_legal_cmds)
        self.basic_commands.update(basic_cmds)

        self.programmer_commands = {}
        self.programmer_commands.update(always_legal_cmds)
        self.programmer_commands.update(basic_cmds)
        self.programmer_commands.update(programmer_cmds)

        self.scientific_commands = {}
        self.scientific_commands.update(always_legal_cmds)
        self.scientific_commands.update(basic_cmds)
        self.scientific_commands.update(scientific_cmds)

        self.commands_that_dont_affect_stack = (self.help, self.change_mode)
        self.base = globals.DEC
        self.mode, self.prev_mode = globals.PROGRAMMER, globals.PROGRAMMER
        self.help_str = self.gen_help_str()
        self.that_was_me = False
        self.edit_region_start = 0

    #--------------------------------------------
    def get_legal_commands(self):
        return {
            globals.BASIC: self.basic_commands,
            globals.PROGRAMMER: self.programmer_commands,
            globals.SCIENTIFIC: self.scientific_commands,
            globals.HELP: self.all_commands,
            globals.CHANGE_MODE: self.mode_commands
        }[self.mode]

    #--------------------------------------------
    def on_activated_async(self, view):
        if(not self.that_was_me and view.name() == globals.RPN_WINDOW_NAME):
            self.update_rpn(view)
            self.that_was_me = False

    #--------------------------------------------
    # def on_close(self, view):
    #     if(view.name() == globals.RPN_WINDOW_NAME):
    #         print("Eeek, I'm dead")

    #--------------------------------------------
    def on_modified(self, view):
        if(view.name() == globals.RPN_WINDOW_NAME):
            if self.that_was_me:
                self.that_was_me = False
                self.edit_region_start = view.size()

            else:
                # handle case where delete occurred before edit region
                if view.size() < self.edit_region_start:
                    self.update_rpn(view)
                    return

                current_region = sublime.Region(self.edit_region_start, view.size())
                text = view.substr(current_region)

                # if in help mode, then remove the help and re-draw the panel
                if self.mode == globals.HELP:
                    self.mode = self.prev_mode
                    self.update_rpn(view)
                    return
                elif self.mode == globals.CHANGE_MODE:
                    # this is if colon (:) was previously pressed
                    try:
                        mode_cmd = self.mode_commands[text]
                    except KeyError:
                        self.update_rpn(view)
                        return
                    mode_cmd()
                    self.update_rpn(view)
                    return

                # if a command key is entered, then run the command and clear the input panel
                else:
                    self.handle_text_input(text, view)

    #--------------------------------------------
    def handle_text_input(self, text, view):
        """
        Check the text input to see if:
        a) the last key pressed was a command-key (a legal one, based on the mode),
        b) the last key pressed was return
        In either case, process the arguments and update the RPN window
        """

        try:
            key = text[-1]
        except IndexError:
            return

        legal_commands = {
            globals.BASIC:      self.basic_commands,
            globals.PROGRAMMER: self.programmer_commands,
            globals.SCIENTIFIC: self.scientific_commands
        }[self.mode]

        args = None
        if key in legal_commands.keys():
            if len(text) > 1:
                args = text[:-1], legal_commands[text[-1]]
            else:
                args = (legal_commands[text[-1]], )
        elif key == '\n':
            # if only whitespace, then ignore
            text = text.strip()
            if not text:
                self.update_rpn(view)
                return
            args = (text,)

        if args is not None:
            self.process(args)
            self.update_rpn(view)

    #--------------------------------------------
    def update_rpn(self, view):
        "Runs the print_to_rpn command"

        self.that_was_me = True
        view.run_command("print_to_rpn", {'stack': self.stack, 'mode': self.mode, 'prev_mode': self.prev_mode, 'help_str': self.help_str, 'base': self.base})

    #--------------------------------------------
    def gen_help_str(self):
        "Returns the help string based on all of the available commands"

        h_txt = "{:^30}\n\n".format("RPN Commands")
        legal_commands = self.get_legal_commands()
        command_keys = sorted(legal_commands.keys())
        for key in command_keys:
            cmd = legal_commands[key]
            h_txt += "\t{} : {}\n".format(key, cmd.__doc__)
        h_txt += "\n{:^30}".format("Any key to exit.")
        return h_txt

    #--------------------------------------------
    def convert_text_to_args(self, text):
        "Convert the text from the input panel into a list of arguments, working back-to-front."
        text_args = []
        while len(text) and text[-1] in self.get_legal_commands().keys():
            text_args.insert(0, text[-1])
            text = text[:-1]
        if text:
            text_args.insert(0, text)
        return text_args

    #--------------------------------------------
    def process(self, args):
        "Take all values and commands supplied from the input and process them to create the new stack."

        for arg in args:
            if type(arg) is str:
                try:
                    if self.mode == globals.PROGRAMMER:
                        last_val = int(arg, self.base)
                    else:
                        last_val = float(arg)
                except ValueError:
                    sublime.error_message("Unable to convert {} to a number.".format(arg))
                else:
                    self.prev_stack.append(self.stack[:])
                    self.stack.append(last_val)
            else:
                self.run_command(arg)

    #--------------------------------------------
    def erase_line(self):
        "Erase the current input line"
        pass

    #--------------------------------------------
    def run_command(self, command):
        try:
            if command not in self.commands_that_dont_affect_stack:
                self.prev_stack.append(self.stack[:])
            command()
        except InsufficientStackDepth as exc:
            sublime.error_message("Not enough values for operation:\n{} required, but only {} available.".format(exc.required, len(self.stack)))

    #--------------------------------------------
    def pop_values(self, count):
        if count <= 0:
            sublime.error_message("Programmer Error, count={}".format(count))

        if len(self.stack) < count:
            self.erase_line()
            raise InsufficientStackDepth(count)

        vals = []
        for cnt in range(count):
            vals.append(self.stack.pop())
        return vals

    #--------------------------------------------
    def change_mode(self):
        "Press : to change calculator modes and bases."

        self.prev_mode = self.mode
        self.mode = globals.CHANGE_MODE

    #--------------------------------------------
    def quit_change_mode(self):
        "Press : again to exit change mode."

        self.mode = self.prev_mode

    #--------------------------------------------
    def add(self):
        "Adds x+y"

        vals = self.pop_values(2)
        self.stack.append(vals[0]+vals[1])

    #--------------------------------------------
    def subtract(self):
        "Subtracts x-y"

        vals = self.pop_values(2)
        self.stack.append(vals[1]-vals[0])

    #--------------------------------------------
    def multiply(self):
        "Multiplies x*y"

        vals = self.pop_values(2)
        self.stack.append(vals[1]*vals[0])

    #--------------------------------------------
    def divide(self):
        "Divides x/y"

        vals = self.pop_values(2)
        try:
            self.stack.append(vals[1]/vals[0])
        except ZeroDivisionError:
            sublime.error_message("Unable to divide by zero")
            self.undo()

    #--------------------------------------------
    def modulo(self):
        "Calculates the remainder of x/y"

        vals = self.pop_values(2)
        try:
            self.stack.append(vals[1] % vals[0])
        except ZeroDivisionError:
            sublime.error_message("Unable to divide by zero")
            self.undo()

    #--------------------------------------------
    def help(self):
        "Displays this help screen."

        if self.mode != globals.HELP:
            self.prev_mode = self.mode
            self.help_str = self.gen_help_str()
        self.mode = globals.HELP

    #--------------------------------------------
    def shift_left(self):
        "Shift left: x << 1"

        vals = self.pop_values(1)
        self.stack.append(vals[0]*2)

    #--------------------------------------------
    def shift_right(self):
        "Shift right: x >> 1"

        vals = self.pop_values(1)
        self.stack.append(vals[0]/2)

    #--------------------------------------------
    def or_func(self):
        "Bitwise OR: x | y"

        vals = self.pop_values(2)
        self.stack.append(vals[1] | vals[0])

    #--------------------------------------------
    def and_func(self):
        "Bitwise AND: x & y"

        vals = self.pop_values(2)
        self.stack.append(vals[1] & vals[0])

    #--------------------------------------------
    def xor(self):
        "Bitwise XOR: x ^ y"

        vals = self.pop_values(2)
        self.stack.append(vals[1] ^ vals[0])

    #--------------------------------------------
    def not_func(self):
        "Bitwise NOT: ~x"

        vals = self.pop_values(1)
        self.stack.append(~vals[0])

    #--------------------------------------------
    def exponent(self):
        "Computes x^y"

        vals = self.pop_values(2)
        try:
            result = math.pow(vals[1], vals[0])
        except Exception as exp:
            sublime.error_message("math error: {}^{}\n{}".format(vals[1], vals[0], exp))
        else:
            self.stack.append(result)

    #--------------------------------------------
    def undo(self):
        "Retrieves previous stack"

        if len(self.prev_stack) == 0:
            sublime.error_message("No previous stack available.")
            return

        self.stack = self.prev_stack.pop()

    #--------------------------------------------
    def clear_stack(self):
        "Clears the stack"

        self.stack = []

    #--------------------------------------------
    def swap_stack(self):
        "Swaps the last two values on the stack"

        x, y = self.pop_values(2)
        self.stack.extend([x, y])

    #--------------------------------------------
    def mode_basic(self):
        "Changes to the basic mode"

        self.mode = globals.BASIC

    #--------------------------------------------
    def mode_programmer(self):
        "Changes to the programmer mode"

        self.mode = globals.PROGRAMMER

    #--------------------------------------------
    def mode_scientific(self):
        "Changes to the scientific mode"

        self.mode = globals.SCIENTIFIC

    #--------------------------------------------
    def decimal(self):
        "Changes base to decimal"

        self.mode = self.prev_mode
        self.base = globals.DEC

    #--------------------------------------------
    def octal(self):
        "Changes base to octal"

        self.mode = self.prev_mode
        self.base = globals.OCT

    #--------------------------------------------
    def hexadecimal(self):
        "Changes base to hexadecimal"

        self.mode = self.prev_mode
        self.base = globals.HEX

    #--------------------------------------------
    def binary(self):
        "Changes base to binary"

        self.mode = self.prev_mode
        self.base = globals.BIN
