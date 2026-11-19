#!/usr/bin/env python3
"""Bad fixture: no usable --json mode (planted failure: json_output).

Accepts --json but always prints plain text, so the output never parses
as JSON. Every other behaviour matches the good fixture.
"""
import json
import os
import sys

HELP = """usage: bad_json_cli <command> [options]

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
    if not sys.stdin.isatty():
        return True
    sys.stdout.write("Proceed? [y/N] ")
    sys.stdout.flush()
    return sys.stdin.readline().strip().lower() in ("y", "yes")


def cmd_list(args):
    items = list_items()
    # PLANTED BUG: --json is ignored; plain text is always printed.
    if items:
        print("items: " + ", ".join(items))
    else:
        print("items: none")
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
    dry_run = "--dry-run" in args
    if not maybe_prompt("--yes" in args, dry_run):
        print("aborted", file=sys.stderr)
        return 1
    if dry_run:
        print("would create: " + name)
        return 0
    write_item(name)
    # PLANTED BUG: deterministic plain text even when --json was passed.
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
