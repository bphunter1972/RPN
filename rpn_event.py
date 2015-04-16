"""
Handles all RPN events.
"""

import sublime
import sublime_plugin
import math
from . import rpn_globals as glb
from .rpn_decorators import *

########################################################################################
class RPNEvent(sublime_plugin.EventListener):
    "Handles all the work for RPN"

    def __init__(self):
        "Initial set-up"

        super(RPNEvent, self).__init__()

        self.opanel = None
        self.done = False
        self.prev_stack, self.stack = [], []
        self.additional_help = {}

        # Create dictionaries of commands that associate key presses with the functions they call
        fundamental_cmds = {
            'U': self.undo,
            'X': self.clear_stack,
            'S': self.swap_stack,
            'x': self.pop_last_value,
            '?': self.help,
            ':': self.change_mode,
        }

        basic_cmds = {
            '+': self.add,
            '-': self.subtract,
            '*': self.multiply,
            '/': self.divide,
            '%': self.modulo,
            'n': self.negate,
        }

        programmer_cmds = {
            '|': self.or_func,
            '&': self.and_func,
            '~': self.not_func,
            '^': self.xor,
            '$': self.field_bits,
            ',': self.shift_left,
            '.': self.shift_right,
            '<': self.shift_left_many,
            '>': self.shift_right_many
        }

        scientific_cmds = {
            '^': self.exponent,
            '!': self.factorial,
            'q': self.square,
            'r': self.root,
            'l': self.log2,
            'L': self.logn,
            'I': self.inverse,
        }

        stats_cmds = {
            's': self.sum,
            'a': self.avg,
            'm': self.median,
        }

        self.mode_commands = {
            'D': self.decimal,
            'H': self.hexadecimal,
            'O': self.octal,
            'B': self.binary,
            'b': self.mode_basic,
            'P': self.mode_programmer,
            'S': self.mode_scientific,
            's': self.mode_stats,
            'R': self.regular_notation,
            'E': self.engineering_notation,
            ':': self.quit_change_mode
        }

        # Build these dictionaries to create command libraries based on modes
        self.basic_commands = {}
        self.basic_commands.update(fundamental_cmds)
        self.basic_commands.update(basic_cmds)
        self.basic_commands_group = (('Fundamental Commands', fundamental_cmds),
                                     ('Basic Commands', basic_cmds),
                                     )

        self.programmer_commands = {}
        self.programmer_commands.update(fundamental_cmds)
        self.programmer_commands.update(basic_cmds)
        self.programmer_commands.update(programmer_cmds)
        self.programmer_commands_group = (('Fundamental Commands', fundamental_cmds),
                                          ('Basic Commands', basic_cmds),
                                          ('Programmer Commands', programmer_cmds),
                                          )

        self.scientific_commands = {}
        self.scientific_commands.update(fundamental_cmds)
        self.scientific_commands.update(basic_cmds)
        self.scientific_commands.update(scientific_cmds)
        self.scientific_commands_group = (('Fundamental Commands', fundamental_cmds),
                                          ('Basic Commands', basic_cmds),
                                          ('Scientific Commands', scientific_cmds),
                                          )
        self.additional_help[glb.SCIENTIFIC] = '\n'.join(("    E : Exponential Notation",
                                                          "    e : Euler's number (2.71828)",
                                                          "    p : pi (3.14159)")) + '\n'

        self.stats_commands = {}
        self.stats_commands.update(fundamental_cmds)
        self.stats_commands.update(basic_cmds)
        self.stats_commands.update(stats_cmds)
        self.stats_commands_group = (('Fundamental Commands', fundamental_cmds),
                                     ('Basic Commands', basic_cmds),
                                     ('Statistical Commands', stats_cmds),
                                     )

        # yes, undo affects the stack. But if it's not in this tuple, then it will
        # not work because it would push the current stack onto prev_stack before popping
        self.commands_that_dont_affect_stack = (self.help, self.change_mode, self.undo)

        self.legal_commands = {
            glb.BASIC:      self.basic_commands,
            glb.PROGRAMMER: self.programmer_commands,
            glb.SCIENTIFIC: self.scientific_commands,
            glb.STATS:      self.stats_commands,
        }
        self.legal_command_groups = {
            glb.BASIC:      self.basic_commands_group,
            glb.PROGRAMMER: self.programmer_commands_group,
            glb.SCIENTIFIC: self.scientific_commands_group,
            glb.STATS:      self.stats_commands_group,
        }

        # Set defaults
        self.base = glb.DEC
        self.notation = glb.REGULAR
        self.mode, self.prev_mode = glb.PROGRAMMER, glb.PROGRAMMER
        self.help_str = None
        self.that_was_me = False
        self.edit_region_start = 0
        self.message = glb.BASIC_HELP

    #--------------------------------------------
    def get_legal_digits(self, text):
        "As as string, return all of the legal digits that can be pressed while in the given modes."

        # exp_mode allows negative numbers after exponents, by using the minus symbol

        exp_mode = True if len(text) >= 2 and text[-2] == 'E' else False
        return {
            glb.BASIC:      '0123456789.',
            glb.PROGRAMMER: {
                glb.BIN:    '01',
                glb.OCT:    '01234567',
                glb.DEC:    '0123456789',
                glb.HEX:    '0123456789abcdefABCDEF'
            }[self.base],
            glb.SCIENTIFIC: ('0123456789.epE' if not exp_mode else '0123456789.-'),
            glb.STATS:      '0123456789.',
        }[self.mode]

    #--------------------------------------------
    def on_activated_async(self, view):
        "Update the rpn window whenever it is activated"

        if(not self.that_was_me and view.name() == glb.RPN_WINDOW_NAME):
            self.update_rpn(view)
            self.that_was_me = False

    #--------------------------------------------
    def on_close(self, view):
        "If the RPN window is closed, re-initialize all values and next time start fresh."

        if(view.name() == glb.RPN_WINDOW_NAME):
            self.__init__()

    #--------------------------------------------
    def on_modified(self, view):
        if(view.name() == glb.RPN_WINDOW_NAME):
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
                if self.mode == glb.HELP:
                    self.mode = self.prev_mode
                    self.update_rpn(view)
                    return
                elif self.mode == glb.CHANGE_MODE:
                    # this is if colon (:) was previously pressed
                    try:
                        mode_cmd = self.mode_commands[text]
                    except KeyError:
                        pass
                    else:
                        mode_cmd()
                    finally:
                        self.update_rpn(view)

                # if a command key or return is entered, then run the command and clear the input panel
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
            key_pressed = text[-1]
        except IndexError:
            return

        args = None
        current_legal_commands = self.legal_commands[self.mode]
        if key_pressed in self.get_legal_digits(text):
            return
        elif key_pressed in current_legal_commands.keys():
            if len(text) > 1:
                args = text[:-1], current_legal_commands[text[-1]]
            else:
                args = (current_legal_commands[text[-1]], )
        elif key_pressed in ' \n':
            # if only whitespace, then ignore
            text = text.strip()
            if not text:
                self.update_rpn(view)
                return
            args = (text,)
        else:
            self.message = "ERROR:  Illegal digit or command {}".format(key_pressed)
            return

        if args is not None:
            self.process(args)
            self.update_rpn(view)

    #--------------------------------------------
    def update_rpn(self, view):
        "Runs the print_to_rpn command"

        self.that_was_me = True
        try:
            view.run_command("print_to_rpn", {'stack': self.stack,
                                              'mode': self.mode,
                                              'prev_mode': self.prev_mode,
                                              'help_str': self.help_str,
                                              'base': self.base,
                                              'notation': self.notation,
                                              'message': self.message})
        except Exception as exc:
            self.message = "ERROR:  Sublime exception: {}".format(exc)

    #--------------------------------------------
    def gen_help_str(self):
        "Returns the help string based on all of the available commands"

        h_txt = "{:^30}\n\n".format("RPN Commands")
        command_groups = self.legal_command_groups[self.mode]
        for group_name, group in command_groups:
            command_keys = sorted(group.keys())
            h_txt += "{:<30}\n".format(group_name)
            for key in command_keys:
                cmd = group[key]
                h_txt += "\t{} : {}\n".format(key, cmd.__doc__)
            h_txt += "\n"

        # Additional Text
        try:
            h_txt += self.additional_help[self.mode]
        except KeyError:
            pass

        h_txt += "\n{:^30}\n\n{:30}\n{:30}\n".format("Any key to exit.",
                                                     "Report Bugs to:",
                                                     "https://github.com/bphunter1972/RPN/issues")
        return h_txt

    #--------------------------------------------
    def convert_text_to_args(self, text):
        "Convert the text from the input panel into a list of arguments, working back-to-front."
        text_args = []
        while len(text) and text[-1] in self.legal_commands[self.mode].keys():
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
                    if self.mode == glb.PROGRAMMER:
                        last_val = int(arg, self.base)
                    elif self.mode == glb.SCIENTIFIC and arg == 'p':
                        last_val = math.pi
                    elif self.mode == glb.SCIENTIFIC and arg == 'e':
                        last_val = math.e
                    else:
                        last_val = float(arg)
                except ValueError:
                    self.message = "ERROR:  Unable to convert {} to a number.".format(arg)
                else:
                    self.prev_stack.append(self.stack[:])
                    self.stack.append(last_val)
            else:
                try:
                    self.message = glb.BASIC_HELP
                    self.run_command(arg)
                except ZeroDivisionError:
                    self.message = "ERROR:  Division by zero."
                except:
                    raise

    #--------------------------------------------
    def run_command(self, command):
        try:
            if command not in self.commands_that_dont_affect_stack:
                self.prev_stack.append(self.stack[:])
            command()
        except glb.InsufficientStackDepth as exc:
            self.message = "ERROR:  Not enough values for operation: {} required, but only {} available.".format(exc.required, len(self.stack))

    #--------------------------------------------
    def pop_values(self, count):
        if count <= 0:
            self.message = "ERROR:  Programmer Error, count={}".format(count)

        if len(self.stack) < count:
            raise glb.InsufficientStackDepth(count)

        vals = []
        for cnt in range(count):
            vals.append(self.stack.pop())
        return vals

    #--------------------------------------------
    def pop_all(self):
        "Clears and returns the entire stack"
        if len(self.stack) == 0:
            raise glb.InsufficientStackDepth()

        vals = self.stack[:]
        self.stack = []
        return vals

    ########################################################################################
    # Fundamental Commands

    #--------------------------------------------
    def change_mode(self):
        "Press colon to change calculator modes and bases."

        self.prev_mode = self.mode
        self.mode = glb.CHANGE_MODE

    #--------------------------------------------
    def quit_change_mode(self):
        "Press colon again to exit change mode."

        self.mode = self.prev_mode

    #--------------------------------------------
    def help(self):
        "Display this help screen."
        if self.mode != glb.HELP:
            self.prev_mode = self.mode
            self.help_str = self.gen_help_str()
        self.mode = glb.HELP

    #--------------------------------------------
    def undo(self):
        "Undo: Retrieves previous stack"
        if len(self.prev_stack) == 0:
            self.message = "ERROR:  No previous stack available."
            return

        self.stack = self.prev_stack.pop()

    #--------------------------------------------
    def clear_stack(self):
        "Clear the stack"
        self.stack = []

    #--------------------------------------------
    @pop_vals(2)
    def swap_stack(self, vals):
        "Swap the last two values on the stack"
        self.stack.extend([vals[0], vals[1]])

    #--------------------------------------------
    def pop_last_value(self):
        "Pop the last value from the stack and discards it"
        self.pop_values(1)

    ########################################################################################
    # Basic Commands

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc
    def add(self, vals):
        "Add x+y"
        return vals[0]+vals[1]

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc
    def subtract(self, vals):
        "Subtract x-y"
        return vals[1]-vals[0]

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc
    def multiply(self, vals):
        "Multiply x*y"
        return vals[1]*vals[0]

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc_undo
    def divide(self, vals):
        "Divide x/y"
        return vals[1]/vals[0]

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc_undo
    def modulo(self, vals):
        "Calculate the remainder of x/y"
        return vals[1] % vals[0]

    #--------------------------------------------
    @pop_vals(1)
    @handle_exc
    def negate(self, vals):
        "Negate: Negate the current value: -x"
        return -vals[0]

    ########################################################################################
    # Programmer Commands

    #--------------------------------------------
    @pop_vals(3)
    @handle_exc_undo
    def field_bits(self, vals):
        "Display field of bits: x[y:z]"
        self.message = "x[y:z]"

        if vals[0] > vals[1]:
            self.message = "Values must be MSB first, LSB second: x[y:z]"

        diff = vals[1] - vals[0]
        mask = 1
        for n in range(diff):
            mask <<= 1
            mask |= 1

        return (vals[2] >> vals[0]) & mask

    #--------------------------------------------
    @pop_vals(1)
    @handle_exc
    def shift_left(self, vals):
        "Shift left: x << 1"
        self.message = "x << 1"
        return vals[0] << 1

    #--------------------------------------------
    @pop_vals(1)
    @handle_exc
    def shift_right(self, vals):
        "Shift right: x >> 1"
        self.message = "x >> 1"
        return vals[0] >> 1

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc
    def shift_left_many(self, vals):
        "Shift left: x << y"
        self.message = "x << y"
        return vals[1] << vals[0]

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc
    def shift_right_many(self, vals):
        "Shift right: x >> y"
        self.message = "x >> y"
        return vals[1] >> vals[0]

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc
    def or_func(self, vals):
        "Bitwise OR: x | y"
        self.message = "x | y"
        return vals[1] | vals[0]

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc
    def and_func(self, vals):
        "Bitwise AND: x & y"
        self.message = "x & y"
        return vals[1] & vals[0]

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc
    def xor(self, vals):
        "Bitwise XOR: x ^ y"
        self.message = "x ^ y"
        return vals[1] ^ vals[0]

    #--------------------------------------------
    @pop_vals(1)
    @handle_exc
    def not_func(self, vals):
        "Bitwise NOT: ~x"
        self.message = "~x"
        mask = int('1' * glb.BIN_MAX_BITS, base=2)
        return(~int(vals[0]) & mask)

    ########################################################################################
    # Scientific Commands

    #--------------------------------------------
    @pop_vals(2)
    @handle_exc
    def exponent(self, vals):
        "Exponent: Computes x^y"
        self.message = "x^y"
        return math.pow(vals[1], vals[0])

    #--------------------------------------------
    @pop_vals(1)
    @handle_exc
    def factorial(self, vals):
        "Factorial: Find x!"
        self.message = "x!"
        return math.factorial(vals[0])

    #--------------------------------------------
    @pop_vals(1)
    @handle_exc
    def square(self, vals):
        "Square: Compute x^2"
        self.message = "x^2"
        return math.pow(vals[0], 2)

    #--------------------------------------------
    @pop_vals(1)
    @handle_exc
    def log2(self, vals):
        "log2: Compute log2(x)"
        self.message = "log2(x)"
        return math.log(vals[0], 2)

    #--------------------------------------------
    @pop_vals(1)
    @handle_exc
    def logn(self, vals):
        "ln: Compute natural log ln(x)"
        self.message = "ln(x)"
        return math.log(vals[0])

    #--------------------------------------------
    @pop_vals(1)
    @handle_exc
    def root(self, vals):
        "Square root: Compute sqrt(x)"
        self.message = "sqrt(x)"
        return math.sqrt(vals[0])

    #--------------------------------------------
    @pop_vals(1)
    @handle_exc
    def inverse(self, vals):
        "Inverse: Compute 1/x"
        self.message = "1/x"
        return (1/vals[0])

    ########################################################################################
    # Statistical Commands

    #--------------------------------------------
    @pop_all_vals
    @handle_exc
    def sum(self, vals):
        "Sum: Returns the sum of all values in the stack."
        self.message = "SUM"
        return sum(vals)

    #--------------------------------------------
    @pop_all_vals
    @handle_exc
    def avg(self, vals):
        "Average/Mean: Returns the mean of all values in the stack."
        self.message = "AVG"
        return sum(vals)/len(vals)

    #--------------------------------------------
    @pop_all_vals
    @handle_exc
    def median(self, vals):
        "Median: Returns the median of all values in the stack."
        self.message = "MEDIAN"
        vals = sorted(vals)
        midpoint = int((len(vals)+1)/2)
        if len(vals) % 2 == 0:
            x, y = vals[midpoint], vals[midpoint-1]
            return (x+y)/2
        else:
            return vals[midpoint-1]

    ########################################################################################
    # Modes

    #--------------------------------------------
    def mode_basic(self):
        "Change to basic mode"
        self.mode = glb.BASIC

    #--------------------------------------------
    def mode_programmer(self):
        "Change to programmer mode"
        self.mode = glb.PROGRAMMER

    #--------------------------------------------
    def mode_scientific(self):
        "Change to scientific mode"
        self.mode = glb.SCIENTIFIC

    #--------------------------------------------
    def mode_stats(self):
        "Change to statistical mode"
        self.mode = glb.STATS

    #--------------------------------------------
    def decimal(self):
        "Set base to decimal"
        self.mode = self.prev_mode
        self.base = glb.DEC

    #--------------------------------------------
    def octal(self):
        "Set base to octal"
        self.mode = self.prev_mode
        self.base = glb.OCT

    #--------------------------------------------
    def hexadecimal(self):
        "Set base to hexadecimal"
        self.mode = self.prev_mode
        self.base = glb.HEX

    #--------------------------------------------
    def binary(self):
        "Set base to binary"
        self.mode = self.prev_mode
        self.base = glb.BIN

    #--------------------------------------------
    def regular_notation(self):
        "Set to regular scientific notation."
        self.mode = self.prev_mode
        self.notation = glb.REGULAR

        #--------------------------------------------
    def engineering_notation(self):
        "Set to engineering scientific notation."
        self.mode = self.prev_mode
        self.notation = glb.ENGINEERING
