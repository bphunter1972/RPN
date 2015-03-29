"""
An RPN Calculator
"""
from __future__ import print_function

import sublime
import sublime_plugin
import math


__author__ = 'Brian Hunter'
__email__ = 'brian.p.hunter@gmail.com'
__version__ = '0.1'


########################################################################################
# Globals
RPN_WINDOW_NAME = ">> rpn <<"
BASES = (BIN, OCT, DEC, HEX) = (2, 8, 10, 16)
MODES = (BASIC, PROGRAMMER, SCIENTIFIC, HELP, CHANGE_MODE) = range(5)

########################################################################################
class InsufficientStackDepth(Exception):
    "Raised when a command requires more values than are on the stack."

    def __init__(self, required):
        self.required = required

########################################################################################
class RpnCommand(sublime_plugin.WindowCommand):
    """
    Stuff goes here
    """

    def __init__(self, *args, **kwargs):
        super(RpnCommand, self).__init__(*args, **kwargs)

        self.opanel = None
        self.done = False
        self.prev_stack, self.stack = [], []

        self.commands = {
            '+': self.add,
            '-': self.subtract,
            '*': self.multiply,
            '/': self.divide,
            '<': self.shift_left,
            '>': self.shift_right,
            '|': self.or_func,
            '&': self.and_func,
            'x': self.xor,
            '~': self.not_func,
            '^': self.exponent,

            # modes
            ':': self.change_mode,

            # stack
            'U': self.undo,
            'C': self.clear_stack,
            '?': self.help,
            'q': self.quit
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

        self.commands_that_dont_affect_stack = 'DHB?Uq'
        self.base = DEC
        self.mode, self.prev_mode = PROGRAMMER, PROGRAMMER
        self.help_str = self.gen_help_str()

    #--------------------------------------------
    def run(self):
        for aview in self.window.views():
            if aview.name() == RPN_WINDOW_NAME:
                self.opanel = aview
                self.window.focus_view(self.opanel)
                break

        if self.opanel is None:
            self.opanel = self.window.new_file()
            self.opanel.set_name(RPN_WINDOW_NAME)
            self.opanel.set_read_only(True)
            self.opanel.settings().set('last_point', 0)
            self.opanel.set_scratch(True)

        self.window.focus_view(self.opanel)
        self.ipanel = self.window.show_input_panel("%5d> " % len(self.stack), "", self.on_done, self.on_change, self.on_cancel)
        self.ipanel_id = self.ipanel.id()
        self.update_rpn()

    #--------------------------------------------
    def update_rpn(self):
        "Runs the print_to_rpn command"
        
        self.opanel.run_command("print_to_rpn", args={'stack': self.stack, 'mode': self.mode, 'help_str': self.help_str, 'base': self.base})

    #--------------------------------------------
    def on_done(self, text):
        "Called when enter is pressed on the input panel"

        text_args = self.convert_text_to_args(text)

        self.process(text_args)

        # send the new stack and status to the RPN window
        self.update_rpn()

        # go fetch another command
        self.run()

    #--------------------------------------------
    def on_change(self, text):
        "Called when any key is pressed on the input panel"

        # catch what happens when the input panel is cleared
        if text == '':
            return

        # on any character, if help_str is populated, then
        # remove the help and erase the panel
        if self.mode == HELP:
            self.mode = self.prev_mode
            self.update_rpn()
            self.erase_input_panel()
            return
        elif self.mode == CHANGE_MODE:
            mode_cmd = self.mode_commands[text]
            mode_cmd()
            self.update_rpn()
            self.erase_input_panel()
            return

        # if a command key is entered, then run the command and clear the input panel
        if text[0] in self.commands.keys():
            self.run_command(text[0])
            self.update_rpn()
            self.erase_input_panel()

    #--------------------------------------------
    def on_cancel(self):
        "Called when 'ESC' is pressed in the input panel"

        self.quit()

    #--------------------------------------------
    def gen_help_str(self):
        "Returns the help string based on all of the available commands"

        h_txt = "{:^30}\n\n".format("RPN Commands")
        command_keys = sorted(self.commands.keys())
        for key in command_keys:
            cmd = self.commands[key]
            h_txt += "\t{} : {}\n".format(key, cmd.__doc__)
        h_txt += "\n{:^30}".format("Any key to exit.")
        return h_txt

    #--------------------------------------------
    def erase_input_panel(self):
        self.ipanel.run_command("erase_input_panel")

    #--------------------------------------------
    def convert_text_to_args(self, text):
        "Convert the text from the input panel into a list of arguments, working back-to-front."
        text_args = []
        while len(text) and text[-1] in self.commands.keys():
            text_args.insert(0, text[-1])
            text = text[:-1]
        if text:
            text_args.insert(0, text)
        return text_args

    #--------------------------------------------
    def process(self, text_args):
        "Take all values and commands supplied from the input panel and process them to create the new stack."

        for arg in text_args:
            try:
                last_val = int(arg, self.base)
                self.prev_stack.append(self.stack[:])
                self.stack.append(last_val)
            except ValueError:
                self.run_command(arg)

    #--------------------------------------------
    def run_command(self, key):
        try:
            command = self.commands[key]
            if key not in self.commands_that_dont_affect_stack:
                self.prev_stack.append(self.stack[:])
            command()
        except KeyError:
            sublime.error_message("Unknown command: %s" % key)
        except InsufficientStackDepth as exc:
            sublime.error_message("Not enough values for operation:\n{} required, but only {} available.".format(exc.required, len(self.stack)))

    #--------------------------------------------
    def pop_values(self, count):
        if count <= 0:
            sublime.error_message("Programmer Error, count={}".format(count))

        if len(self.stack) < count:
            self.erase_input_panel()
            raise InsufficientStackDepth(count)

        vals = []
        for cnt in range(count):
            vals.append(self.stack.pop())
        return vals

    #--------------------------------------------
    def change_mode(self):
        "Press : to change calculator modes and bases."

        self.prev_mode = self.mode
        self.mode = CHANGE_MODE

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
        self.stack.append(vals[1]/vals[0])

    #--------------------------------------------
    def help(self):
        "Displays this help screen."

        if self.mode != HELP:
            self.prev_mode = self.mode
        self.mode = HELP

    #--------------------------------------------
    def shift_left(self):
        "Shift left: x << 1"

        vals = self.pop_values(1)
        self.stack.append(vals[0]*2)

    #--------------------------------------------
    def shift_right(self):
        "Shift right: x >> 1"

        vals = self.pop_values(1)
        self.stack.append(int(vals[0]/2))

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
            result = int(math.pow(vals[1], vals[0]))
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
    def mode_basic(self):
        "Changes to the basic mode"

        self.mode = BASIC

    #--------------------------------------------
    def mode_programmer(self):
        "Changes to the programmer mode"

        self.mode = PROGRAMMER

    #--------------------------------------------
    def mode_scientific(self):
        "Changes to the scientific mode"

        self.mode = SCIENTIFIC

    #--------------------------------------------
    def decimal(self):
        "Changes base to decimal"

        self.mode = self.prev_mode
        self.base = DEC

    #--------------------------------------------
    def octal(self):
        "Changes base to octal"

        self.mode = self.prev_mode
        self.base = OCT

    #--------------------------------------------
    def hexadecimal(self):
        "Changes base to hexadecimal"

        self.mode = self.prev_mode
        self.base = HEX

    #--------------------------------------------
    def binary(self):
        "Changes base to binary"

        self.mode = self.prev_mode
        self.base = BIN

    #--------------------------------------------
    def quit(self):
        "Quit out of RPN"

        if RPN_WINDOW_NAME in [it.name() for it in self.window.views()]:
            self.window.focus_view(self.opanel)
            self.window.run_command("close_file")

        # close the input panel
        self.window.run_command("hide_panel", {"cancel": True})

        # clear these things out
        self.ipanel = None
        self.opanel = None
        self.stack = []
        self.done = True


########################################################################################
class PrintToRpnCommand(sublime_plugin.TextCommand):
    base = None
    mode_bar = ".....{:.<15s}...{:.>5s}......"

    #--------------------------------------------
    def run(self, edit, **kwargs):
        stack = kwargs['stack']
        self.mode = kwargs['mode']
        self.help_str = kwargs['help_str']
        self.base = kwargs['base']
        self.view.set_read_only(False)
        # whole_region = sublime.Region(0, self.view.size())
        self.erase_buffer(edit)
        rpn_txt = self.get_rpn_txt(stack)
        self.view.insert(edit, 0, rpn_txt)
        self.view.set_read_only(True)

    #--------------------------------------------
    def erase_buffer(self, edit):
        region = sublime.Region(0, self.view.size())
        self.view.erase(edit, region)

    #--------------------------------------------
    def get_rpn_txt(self, stack):
        if self.mode == CHANGE_MODE:
            return self.get_change_mode_str()

        str = self.get_mode_line() + "\n\n"
        if self.mode == HELP:
            str += self.help_str
        else:
            if stack:
                for idx, val in enumerate(stack):
                    str += "{}> {}\n".format(idx, self.print_val(val))
            else:
                str += "0> "
        return str

    #--------------------------------------------
    def print_val(self, val):
        base_char = {2: 'b', 8: 'o', 10: 'd', 16: 'X'}[self.base]
        fmt = "{:%s}" % (base_char)
        val_str = fmt.format(int(val))

        if self.base in (2, 8, 16) and len(val_str) > 4:
            vals = []
            while len(val_str):
                vals.insert(0, val_str[-4:])
                val_str = val_str[:-4]
            val_str = '_'.join(vals)

        return val_str

    #--------------------------------------------
    def get_mode_line(self):
        # first, the current status fields
        base_str = {2: "BIN", 8: "OCT", 10: "DEC", 16: "HEX"}[self.base]
        mode_str = {BASIC: "BASIC",
                    PROGRAMMER: "PROGRAMMER",
                    SCIENTIFIC: "SCIENTIFIC",
                    HELP: "",
                    CHANGE_MODE: "",
                    }[self.mode]

        mode_line = self.mode_bar.format(mode_str, base_str)
        return mode_line

    #--------------------------------------------
    def get_change_mode_str(self):
        bar_str  = self.mode_bar.format("(b)ASIC", "(B)IN") + '\n'
        bar_str += self.mode_bar.format("(P)ROGRAMMER", "(O)CT") + '\n'
        bar_str += self.mode_bar.format("(S)CIENTIFIC", "(D)EC") + '\n'
        bar_str += self.mode_bar.format("", "(H)EX") + '\n'

        return bar_str

########################################################################################
class EraseInputPanelCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        curr_region = sublime.Region(0, 1)
        self.view.erase(edit, curr_region)
