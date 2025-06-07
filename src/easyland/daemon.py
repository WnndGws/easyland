import os
import json
import sys
import time
import regex as re
import subprocess
from loguru import logger
from easyland.idle import Idle
from threading import Thread


class Daemon:
    def __init__(self, config):
        self.config = config
        self.listeners = self.get_listeners()
        logger.info("Starting easyland daemon")
        self.threads = []
        self.call_handler("init")

    def setup_tasks(self):
        listener_names = self.listeners.keys()

        if "hyprland" in listener_names:
            t = Thread(target=self.launch_hyprland_daemon, daemon=True)
            t.start()
            self.threads.append(t)

        if "sway" in listener_names:
            if not "event_types" in self.listeners["sway"]:
                logger.error(
                    "No sway event types defined for Sway listeners in the config file"
                )
                sys.exit(1)
            existing_types = [
                "workspace",
                "window",
                "output",
                "mode",
                "barconfig_update",
                "binding",
                "shutdown",
                "tick",
                "bar_state_update",
                "input",
            ]
            for event_type in self.listeners["sway"]["event_types"]:
                if event_type not in existing_types:
                    logger.error("Sway - Invalid event type: " + event_type)
                    sys.exit(1)
                t = Thread(
                    target=self.launch_sway_daemon, args=(event_type,), daemon=True
                )
                t.start()
                self.threads.append(t)

        if "systemd_logind" in listener_names:
            t = Thread(target=self.launch_systemd_login_daemon, daemon=True)
            t.start()
            self.threads.append(t)

        if "idle" in listener_names:
            if callable(getattr(self.config, "idle_config", None)):
                t = Thread(target=self.launch_idle_daemon, daemon=True)
                t.start()
                self.threads.append(t)

    def get_listeners(self):
        if hasattr(self.config, "listeners"):
            return self.config.listeners
        else:
            logger.error("No listeners defined in the config file")
            sys.exit(1)

    def call_handler(self, handler, *argv):
        func = getattr(self.config, handler, None)
        if callable(func):
            func(*argv)

    def launch_idle_daemon(self):
        idle_config = self.config.idle_config()
        idle = Idle(idle_config)
        idle.setup()

    def launch_hyprland_daemon(self):
        logger.info("Launching hyprland daemon")
        socket = self.listeners["hyprland"].get(
            "socket_path",
            "$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock",
        )
        socket = os.path.expandvars(socket)
        logger.info(f"Using Hyprland socket path: {socket}")
        cmd = ["socat", "-U", "-", f"UNIX-CONNECT:{socket}"]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        while True:
            line = proc.stdout.readline()
            if not line:
                err = proc.stderr.read()
                logger.error(f"Error while listening to Hyprland socket: {err}")
                sys.exit(1)
            self.last_event_time = time.time()
            decoded_line = line.strip()
            logger.debug(decoded_line)
            if ">>" in decoded_line:
                data = decoded_line.split(">>", 1)
                self.call_handler("on_hyprland_event", data[0], data[1])

    def launch_sway_daemon(self, event_type):
        logger.info(f"Launching Sway daemon for event type: {event_type}")
        cmd = ["swaymsg", "-m", "-r", "-t", "subscribe", f'["{event_type}"]']
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        while True:
            line = proc.stdout.readline()
            if not line:
                logger.error(
                    f"Sway daemon: subprocess ended unexpectedly for event type {event_type}"
                )
                return
            decoded_line = line.strip()
            try:
                json_output = json.loads(decoded_line)
                self.call_handler(f"on_sway_event_{event_type}", json_output)
            except json.decoder.JSONDecodeError:
                logger.error(f"Sway daemon: Invalid JSON: {decoded_line}")
                logger.error("Sway daemon: Exiting")
                return

    def launch_systemd_login_daemon(self):
        logger.info("Launching systemd daemon")
        cmd = ["gdbus", "monitor", "--system", "--dest", "org.freedesktop.login1"]
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        pattern = re.compile(r"(.+?): ([^\s]+?) \((.*?)\)$")
        while True:
            line = proc.stdout.readline()
            if not line:
                logger.error("Systemd daemon subprocess ended unexpectedly")
                return
            decoded_line = line.strip()
            res = pattern.match(decoded_line)
            if res:
                sender, name, payload = res.groups()
                if "Properties" not in name:
                    signal_name = name.split(".")[-1]
                    f = "on_" + signal_name
                    self.call_handler(f, payload)
                    self.call_handler("on_systemd_event", sender, signal_name, payload)
