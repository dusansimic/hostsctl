import os
import glob
import json
from typing import TypedDict, Sequence
import argparse

CONFIG_FILE_VERSION = "0.1.0"
CONFIG_FILE_PATH = "/etc/hostsctl/config.json"
HOSTS_FILE_PATH = "/etc/hosts"


class HostsEntryDict(TypedDict):
    name: str
    filename: str
    enabled: bool


class ConfigDict(TypedDict):
    version: str
    entries: Sequence[HostsEntryDict]


class Colors:
    RESET = "\033[0m"

    class Foreground:
        RED = "\033[31m"
        GREEN = "\033[32m"


def get_hosts_files():
    files = glob.glob("/etc/hosts.d/*.hosts")
    files = [file for file in files if os.path.isfile(file)]
    return sorted(files)


def get_config() -> ConfigDict:
    config: ConfigDict = {}

    if os.path.isfile(CONFIG_FILE_PATH):
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            config["entries"] = sorted(config["entries"], key=lambda e: e["name"])
        return config
    else:
        config = {
            "version": CONFIG_FILE_VERSION,
            "entries": [],
        }
        return config


def save_config(config: ConfigDict):
    with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f)


def reload_config(config: ConfigDict, hosts_files: Sequence[str]):
    config_files = [entry["filename"] for entry in config["entries"]]
    missing_files = set(config_files) - set(hosts_files)
    new_files = set(hosts_files) - set(config_files)

    new_entries: Sequence[HostsEntryDict] = []

    for entry in config["entries"]:
        if entry["filename"] not in missing_files:
            new_entries.append(entry)

    for new_file in new_files:
        new_entries.append(
            {
                "enabled": False,
                "filename": new_file,
                "name": os.path.basename(new_file)[:-6],
            }
        )

    config["entries"] = sorted(new_entries, key=lambda e: e["name"])


def print_entries_states(config: ConfigDict):
    for entry in config["entries"]:
        color = Colors.Foreground.GREEN if entry["enabled"] else Colors.Foreground.RED
        state = "ENABLED" if entry["enabled"] else "DISABLED"
        print(
            Colors.RESET + "[ " + color + state + Colors.RESET + " ] " + entry["name"]
        )


def reload_hosts_file(config: ConfigDict):
    hosts_file_lines = []

    for entry in config["entries"]:
        if not entry["enabled"]:
            continue

        with open(entry["filename"], "r", encoding="utf-8") as f:
            hosts_file_lines.extend(f.readlines())

    with open(HOSTS_FILE_PATH, "w", encoding="utf-8") as f:
        f.writelines(hosts_file_lines)


def main():
    main_parser = argparse.ArgumentParser(description="utility for managing hosts file")
    subparsers = main_parser.add_subparsers(required=True, dest="command")

    enable_parser = subparsers.add_parser("enable", description="enable a hosts file")
    enable_parser.add_argument("name", help="hosts config name")

    disable_parser = subparsers.add_parser(
        "disable", description="disable a hosts file"
    )
    disable_parser.add_argument("name", help="hosts config name")

    subparsers.add_parser("reload", description="reload hostsctl config and hosts file")
    subparsers.add_parser("status", description="print status of loaded hosts files")

    args = main_parser.parse_args()

    config = get_config()
    if args.command == "enable":
        for entry in config["entries"]:
            if entry["name"] == args.name:
                entry["enabled"] = True
                save_config(config)
                exit()
        print("hosts config '" + args.name + "' doesn't exist")
        exit(1)
    elif args.command == "disable":
        for entry in config["entries"]:
            if entry["name"] == args.name:
                entry["enabled"] = False
                save_config(config)
                exit()
        print("hosts config '" + args.name + "' doesn't exist")
        exit(1)
    elif args.command == "reload":
        hosts_files = get_hosts_files()
        reload_config(config, hosts_files)
        save_config(config)
        reload_hosts_file(config)
    elif args.command == "status":
        print_entries_states(config)


if __name__ == "__main__":
    main()
