from . import command, logger
import subprocess
import os
from pywayland.client import Display
from pywayland.protocol.wayland.wl_seat import WlSeat
from pywayland.protocol.ext_idle_notify_v1 import ExtIdleNotifierV1


class Idle:
    def __init__(self, config):
        self.command = command
        self._config = config
        self._display = Display()
        self._display.connect()
        self._idle_notifier = None
        self._seat = None
        self._notifications = []
        self._notifier_set = False

    def _global_handler(self, reg, id_num, iface_name, version):
        if iface_name == "wl_seat":
            self._seat = reg.bind(id_num, WlSeat, version)
        elif iface_name == "ext_idle_notifier_v1":
            self._idle_notifier = reg.bind(id_num, ExtIdleNotifierV1, version)

        if self._idle_notifier and self._seat and not self._notifier_set:
            self._notifier_set = True
            self._notifications = []
            for idx, (timeout, idle_cmds, *resume_cmds) in enumerate(self._config):
                logger.info(f"Setting idle notifier for {timeout} seconds")
                notification = self._idle_notifier.get_idle_notification(
                    timeout * 1000, self._seat
                )
                notification._index = idx
                notification.dispatcher["idled"] = self._idle_notifier_handler
                notification.dispatcher["resumed"] = self._idle_notifier_resume_handler
                self._notifications.append(notification)

    def _idle_notifier_handler(self, notification):
        for command in self._config[notification._index][1]:
            logger.info(f"Idle - Running command: {command}")
            subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def _idle_notifier_resume_handler(self, notification):
        resume_cmds = (
            self._config[notification._index][2]
            if len(self._config[notification._index]) > 2
            else []
        )
        for command in resume_cmds:
            logger.info(f"Idle - Resuming: Running command: {command}")
            subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def setup(self):
        reg = self._display.get_registry()
        reg.dispatcher["global"] = self._global_handler
        while True:
            self._display.dispatch(block=True)
