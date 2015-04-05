

RPN_WINDOW_NAME = ">> rpn <<"
BASES = (BIN, OCT, DEC, HEX) = (2, 8, 10, 16)
MODES = (BASIC, PROGRAMMER, SCIENTIFIC, HELP, CHANGE_MODE) = range(5)
BIN_MAX_BITS = 48
BIN_MAX_VAL = int('1'*BIN_MAX_BITS, base=2)

########################################################################################
class InsufficientStackDepth(Exception):
    "Raised when a command requires more values than are on the stack."

    def __init__(self, required):
        self.required = required
