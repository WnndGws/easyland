#!/usr/bin/env python3
import argparse
import importlib.util
import sys
import time
from easyland.daemon import Daemon

version = "0.7.6"


def import_from_path(path):
    # Use module name from path basename, replace hyphens with underscores
    module_name = path.rsplit("/", 1)[-1].replace("-", "_").removesuffix(".py")
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules[module_name] = module
    return module


def main():
    parser = argparse.ArgumentParser(
        description="Easyland - A python swiss-knife to manage Wayland compositors like Hyprland and Sway"
    )
    parser.add_argument(
        "-c", "--config", required=True, help="Path to your config file"
    )
    parser.add_argument("-v", "--version", action="store_true", help="Show the version")
    args = parser.parse_args()

    if args.version:
        print(f"Easyland version: {version}")
        sys.exit(0)

    config = import_from_path(args.config)
    daemon = Daemon(config)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
