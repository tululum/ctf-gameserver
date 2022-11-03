#!/usr/bin/env python3

import logging
import socket

from ctf_gameserver import checkerlib


class ExampleChecker(checkerlib.BaseChecker):

    def place_flag(self, tick):
        return checkerlib.CheckResult.OK, ''

    def check_service(self):
        return checkerlib.CheckResult.OK, ''

    def check_flag(self, tick):
        return checkerlib.CheckResult.OK, ''


if __name__ == '__main__':

    checkerlib.run_check(ExampleChecker)
