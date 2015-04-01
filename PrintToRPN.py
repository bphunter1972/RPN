import sublime
import sublime_plugin
from . import globals

# from RPNCalc import globals.BIN, OCT, DEC, HEX

########################################################################################
class PrintToRpnCommand(sublime_plugin.TextCommand):
    base = None
    mode_bar = ".....{:.<15s}...{:.>5s}......"

    #--------------------------------------------
    def run(self, edit, **kwargs):
        stack = kwargs['stack']
        self.mode = kwargs['mode']
        self.prev_mode = kwargs['prev_mode']
        self.help_str = kwargs['help_str']
        self.base = kwargs['base']

        self.erase_buffer(edit)
        rpn_txt = self.get_rpn_txt(stack)
        self.view.insert(edit, 0, rpn_txt)

    #--------------------------------------------
    def erase_buffer(self, edit):
        region = sublime.Region(0, self.view.size())
        self.view.erase(edit, region)

    #--------------------------------------------
    def get_rpn_txt(self, stack):
        if self.mode == globals.CHANGE_MODE:
            return self.get_change_mode_str()

        str = self.get_mode_line() + "\n\n"
        if self.mode == globals.HELP:
            str += self.help_str
        else:
            if stack:
                for idx, val in enumerate(stack):
                    str += "{}> {}\n".format(idx, self.print_val(val))

            str += "{}> ".format(len(stack))

        return str

    #--------------------------------------------
    def print_val(self, val):
        if self.mode == globals.PROGRAMMER:
            base_char = {2: 'b', 8: 'o', 10: 'd', 16: 'X'}[self.base]
            fmt = "{:%s}" % (base_char)
        else:
            fmt = "{:g}"
        if self.mode == globals.PROGRAMMER:
            val = int(val)
        val_str = fmt.format(val)

        if self.mode == globals.PROGRAMMER and self.base in (globals.BIN, globals.OCT, globals.HEX) and len(val_str) > 4:
            vals = []
            while len(val_str):
                vals.insert(0, val_str[-4:])
                val_str = val_str[:-4]
            val_str = '_'.join(vals)

        return val_str

    #--------------------------------------------
    def get_mode_line(self):
        # first, the current status fields
        base_str = {globals.BIN: "BIN", globals.OCT: "OCT", globals.DEC: "DEC", globals.HEX: "HEX"}[self.base] if self.mode == globals.PROGRAMMER else ""
        mode_str = {globals.BASIC: "BASIC",
                    globals.PROGRAMMER: "PROGRAMMER",
                    globals.SCIENTIFIC: "SCIENTIFIC",
                    globals.HELP: "HELP",
                    globals.CHANGE_MODE: "",
                    }[self.mode]

        mode_line = self.mode_bar.format(mode_str, base_str)
        return mode_line

    #--------------------------------------------
    def get_change_mode_str(self):
        if self.prev_mode == globals.PROGRAMMER:
            bar_str  = self.mode_bar.format("(b)ASIC",      "(B)IN") + '\n'
            bar_str += self.mode_bar.format("(P)ROGRAMMER", "(O)CT") + '\n'
            bar_str += self.mode_bar.format("(S)CIENTIFIC", "(D)EC") + '\n'
            bar_str += self.mode_bar.format("",             "(H)EX") + '\n'
        else:
            bar_str  = self.mode_bar.format("(b)ASIC",      "") + '\n'
            bar_str += self.mode_bar.format("(P)ROGRAMMER", "") + '\n'
            bar_str += self.mode_bar.format("(S)CIENTIFIC", "") + '\n'

        return bar_str