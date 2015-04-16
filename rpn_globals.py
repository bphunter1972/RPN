"""
Global variables for RPN.
"""

########################################################################################
# Constants that users may change
# TODO: Make these settings
RPN_WINDOW_NAME = ">> rpn <<"
BIN_MAX_BITS    = 48
SCI_PRECISION   = 10

########################################################################################
# Constants that should not be touched
BASES           = (BIN, OCT, DEC, HEX) = (2, 8, 10, 16)
MODES           = (BASIC, PROGRAMMER, SCIENTIFIC, STATS, HELP, CHANGE_MODE) = range(6)
NOTATIONS       = (REGULAR, ENGINEERING) = range(2)
BIN_MAX_VAL     = int('1'*BIN_MAX_BITS, base=2)
MODE_BAR        = ".....{:.<15s}...{:.>5s}......"
MESSAGE_BAR     = "{:>34s}"
BASIC_HELP      = "? - Help"

########################################################################################
class InsufficientStackDepth(Exception):
    "Raised when a command requires more values than are on the stack."

    def __init__(self, required):
        self.required = required
