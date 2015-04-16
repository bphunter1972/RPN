"""
Decorators used by computational functions.
"""

from functools import wraps
import sublime

########################################################################################
# Decorators

#--------------------------------------------
def pop_vals(pop_num):
    def pop_dec(func):
        @wraps(func)
        def wrapper(self):
            vals = self.pop_values(pop_num)
            func(self, vals)
        return wrapper
    return pop_dec

#--------------------------------------------
def pop_all_vals(func):
    @wraps(func)
    def wrapper(self):
        vals = self.pop_all()
        func(self, vals)
    return wrapper

#--------------------------------------------
def handle_exc(func):
    @wraps(func)
    def wrapper(self, vals):
        try:
            result = func(self, vals)
        except Exception as exp:
            sublime.error_message("math error: {}".format(exp))
        else:
            self.stack.append(result)
    return wrapper

#--------------------------------------------
def handle_exc_undo(func):
    @wraps(func)
    def wrapper(self, vals):
        try:
            self.stack.append(func(self, vals))
        except Exception as exc:
            sublime.error_message("math error: {}".format(exc))
            self.undo()
    return wrapper
