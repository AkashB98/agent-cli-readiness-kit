#!/usr/bin/env python3
"""Bad fixture: blocks on an interactive prompt (planted: non_interactive).

`create` without --yes always prompts, and on EOF it loops forever
instead of giving up, so a non-interactive caller hangs until killed.
Passing --yes (as the other probes do) skips the prompt entirely.
"""
import json
import os
import sys
import time

HELP = """usage: bad_interactive_cli <command> [options]

commands:
  create  Create an item
  list    List items

options:
  --json      Emit JSON output
  --dry-run   Show what would happen without changing anything
  --yes       Skip the confirmation prompt
"""


def data_dir():
    return os.path.join(os.getcwd(), "data")


def write_item(name):
    content = json.dumps({"name": name}, sort_keys=True) + "\n"
    path = os.path.join(data_dir(), name + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            if fh.read() == content:
                return
    os.makedirs(data_dir(), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def list_items():
    d = data_dir()
    if not os.path.isdir(d):
        return []
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".json"))


def maybe_prompt(yes, dry_run):
    if yes or dry_run:
        return True
    # PLANTED BUG: prompt unconditionally; EOF loops forever.
    sys.stdout.write("Proceed? [y/N] ")
    sys.stdout.flush()
    while True:
        line = sys.stdin.readline()
        if line == "":
            time.sleep(0.05)
            continue
        return line.strip().lower() in ("y", "yes")


def cmd_list(args):
    items = list_items()
    if "--json" in args:
        print(json.dumps({"items": items}, sort_keys=True))
    elif items:
        for name in items:
            print(name)
    else:
        print("no items")
    return 0


def cmd_create(args):
    name = None
    i = 0
    while i < len(args):
        if args[i] == "--name" and i + 1 < len(args):
            name = args[i + 1]
            i += 2
        else:
            i += 1
    if not name:
        print("error: create requires --name", file=sys.stderr)
        return 2
    as_json = "--json" in args
    dry_run = "--dry-run" in args
    if not maybe_prompt("--yes" in args, dry_run):
        print("aborted", file=sys.stderr)
        return 1
    if dry_run:
        if as_json:
            print(json.dumps({"dry_run": True, "name": name,
                              "status": "would_create"}, sort_keys=True))
        else:
            print("would create: " + name)
        return 0
    write_item(name)
    if as_json:
        print(json.dumps({"name": name, "status": "created"},
                         sort_keys=True))
    else:
        print("created: " + name)
    return 0


def main(argv):
    if not argv or argv[0] in ("--help", "-h", "help"):
        print(HELP, end="")
        return 0
    if argv[0] == "list":
        return cmd_list(argv[1:])
    if argv[0] == "create":
        return cmd_create(argv[1:])
    print("error: unknown command: " + argv[0], file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
