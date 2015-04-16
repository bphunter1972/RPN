"""
An RPN Calculator with Basic, Programmer, Scientific, and Statistical modes.

Press ? for help
Press : to change modes, bases, or notations.
"""

__author__ = 'Brian Hunter'
__email__ = 'brian.p.hunter@gmail.com'
__version__ = '0.4.0'


import sublime_plugin
from . import rpn_globals as glb

class RpnCommand(sublime_plugin.WindowCommand):
    "Launches the rpn view"

    #--------------------------------------------
    def run(self):
        self.opanel = None
        for aview in self.window.views():
            if aview.name() == glb.RPN_WINDOW_NAME:
                self.opanel = aview
                break

        if self.opanel is None:
            self.opanel = self.window.new_file()
            self.opanel.set_name(glb.RPN_WINDOW_NAME)
            self.opanel.set_scratch(True)

        self.window.focus_view(self.opanel)
