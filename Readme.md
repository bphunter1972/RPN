# RPN

## About

RPN is a reverse-polish notation calculator featuring basic, programmer,
scientific, and statistics modes.

Launch RPN with the rpn command or Ctrl+Command+C (Ctrl+Alt+C in Windows or Linux).

![](/images/RPN.gif)

## Modes

Press ':' to change modes, bases, and scientific notation.

### Basic

Basic mode supports simple addition, subtraction, etc., with floating point
numbers.

### Programmer

Programmer mode supports 4 different bases:  hexadecimal, decimal, octal, and
binary. It also supports commands such as shifting, inversion, AND, OR, and XOR.

Due to Sublime Text 3 limitations, the maximum sized value in programmer mode
is specified in globals.py as BIN_MAX_BITS. It defaults to 48 bits. Using 64
for this constant will cause some issues within Sublime.

### Scientific

Scientific mode operates with floating point numbers and supports commands
such as exponent, factorial, square, square root, log2, etc. 

Scientific notation is supported in regular or Engineering notation. You can
alter the notation from the Modes

### Statistics

Statistical mode has commands sum, average, and median which operate on the
entire stack at once.

## Installation

* Using Package Control, install "RPN"

Or:

* Clone this repository into your Sublime Text Packages folder:

  * OS X: ~/Library/Application Support/Sublime Text 3/Packages/
  * Windows: %APPDATA%/Sublime Text 3/Packages/
  * Linux: ~/.Sublime Text 3/Packages/ or ~/.config/sublime-text-3/Packages

## Help

Help is available within RPN by pressing '?'. Change modes by pressing ':'.

![](/images/help.png)

