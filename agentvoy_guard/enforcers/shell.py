"""
Shell execution blocker.
Monkey-patches subprocess and os.system when allow_shell is False.
"""

from __future__ import annotations
from ..exceptions import ShellBlockedError


class ShellEnforcer:
    def __init__(self, allow_shell: bool, allow_subprocess: bool):
        self.allow_shell = allow_shell
        self.allow_subprocess = allow_subprocess
        self._patches: list = []

    def install(self):
        if not self.allow_shell:
            self._patch_os_system()
        if not self.allow_subprocess:
            self._patch_subprocess()

    def uninstall(self):
        for restore_fn in self._patches:
            restore_fn()
        self._patches.clear()

    def _patch_os_system(self):
        import os
        original = os.system

        def blocked_system(command):
            raise ShellBlockedError(str(command))

        os.system = blocked_system
        self._patches.append(lambda: setattr(os, "system", original))

    def _patch_subprocess(self):
        import subprocess
        original_run = subprocess.run
        original_popen = subprocess.Popen
        original_call = subprocess.call
        original_check = subprocess.check_output

        def blocked(*args, **kwargs):
            cmd = args[0] if args else kwargs.get("args", "")
            raise ShellBlockedError(str(cmd))

        subprocess.run = blocked
        subprocess.Popen = blocked
        subprocess.call = blocked
        subprocess.check_output = blocked

        def restore():
            subprocess.run = original_run
            subprocess.Popen = original_popen
            subprocess.call = original_call
            subprocess.check_output = original_check

        self._patches.append(restore)
