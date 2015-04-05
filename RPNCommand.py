import sublime_plugin

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
