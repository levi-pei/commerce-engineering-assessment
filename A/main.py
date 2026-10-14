from __future__ import annotations

import sys

from A.ledger import run


def main() -> int:
    first_line = sys.stdin.readline().split()
    if len(first_line) != 2:
        print("ERROR: expected initial stock and command count", file=sys.stderr)
        return 2

    try:
        initial_stock, command_count = (int(value) for value in first_line)
    except ValueError:
        print("ERROR: initial stock and command count must be integers", file=sys.stderr)
        return 2

    if initial_stock < 0 or command_count < 1:
        print("ERROR: values are outside the allowed range", file=sys.stderr)
        return 2

    commands = [sys.stdin.readline().rstrip("\n") for _ in range(command_count)]
    print("\n".join(run(initial_stock, commands)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

