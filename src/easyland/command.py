import subprocess
import orjson
import os
from easyland.log import logger
import socket


class Command:
    def sway_get_all_monitors(self):
        return self.exec("swaymsg -t get_outputs", decode_json=True)

    def sway_get_monitor(self, *, name=None, make=None, model=None):
        monitors = self.sway_get_all_monitors()
        if not monitors:
            return None
        for monitor in monitors:
            if name is not None and name in monitor.get("name", ""):
                return monitor
            if make is not None and make in monitor.get("make", ""):
                return monitor
            if model is not None and model in monitor.get("model", ""):
                return monitor
        return None

    def hyprland_get_all_monitors(self):
        return self.exec("hyprctl -j monitors", decode_json=True)

    def get_system_hostname(self):
        return socket.gethostname()

    def hyprland_get_monitor(
        self, *, name=None, description=None, make=None, model=None
    ):
        monitors = self.hyprland_get_all_monitors()
        if not monitors:
            return None
        for monitor in monitors:
            if name is not None and name in monitor.get("name", ""):
                return monitor
            if description is not None and description in monitor.get(
                "description", ""
            ):
                return monitor
            if make is not None and make in monitor.get("make", ""):
                return monitor
            if model is not None and model in monitor.get("model", ""):
                return monitor
        return None

    def exec(self, command, background=False, decode_json=False):
        if background:
            logger.info("Executing background command: " + command)
            with open(os.devnull, "w") as fp:
                subprocess.Popen(command, shell=True, stdout=fp, stderr=fp)
            return True
        else:
            logger.info("Executing command: " + command)
            output = subprocess.check_output(command, shell=True)
            if decode_json:
                try:
                    return orjson.loads(output)
                except orjson.JSONDecodeError:
                    return None
            return output.decode("utf-8")
