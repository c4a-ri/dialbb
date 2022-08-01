#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# error_handlers.py
#   functions for handling errors

__version__ = '0.1'
__author__ = 'Mikio Nakano'
__copyright__ = 'C4A Research Institute, Inc.'

import sys, os

if os.environ.get('DIALBB_DEBUG', 'no').lower() == 'yes':
    DEBUG = True
else:
    DEBUG = False

class BuildError(BaseException):
    pass

def abort_during_building(message: str) -> None:
    '''
    print error message and abort
    :param message:
    '''
    print("Encounterd an error during building app. " + message, file=sys.stdout)
    sys.exit(1)


def warn_during_building(message: str) -> None:
    if DEBUG:
        raise BuildError("Warning found during building app: " + message)
    else:
        print("Warning: " + message, file=sys.stdout)


