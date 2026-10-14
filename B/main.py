from __future__ import annotations

import sys

from B.optimiser import Warehouse, optimise


def main() -> int:
    header = sys.stdin.readline().split()
    if len(header) != 2:
        print("ERROR: expected warehouse count and requested quantity", file=sys.stderr)
        return 2
    try:
        warehouse_count, requested = (int(value) for value in header)
    except ValueError:
        print("ERROR: header values must be integers", file=sys.stderr)
        return 2

    warehouses: list[Warehouse] = []
    try:
        for _ in range(warehouse_count):
            warehouse_id, stock, fixed_cost, unit_cost = sys.stdin.readline().split()
            warehouses.append(Warehouse(warehouse_id, int(stock), int(fixed_cost), int(unit_cost)))
        solution = optimise(warehouses, requested)
    except (ValueError, TypeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if solution is None:
        print("-1")
        return 0

    print(solution.warehouse_count, solution.total_cost)
    for warehouse_id, quantity in solution.allocations:
        print(warehouse_id, quantity)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

