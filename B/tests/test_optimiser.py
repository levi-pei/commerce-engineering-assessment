from __future__ import annotations

import random
import unittest
from itertools import product

from B.optimiser import Solution, Warehouse, optimise


def brute_force(warehouses: list[Warehouse], requested: int) -> Solution | None:
    ordered = sorted(warehouses, key=lambda warehouse: warehouse.warehouse_id)
    candidates: list[Solution] = []
    for quantities in product(*(range(warehouse.stock + 1) for warehouse in ordered)):
        if sum(quantities) != requested:
            continue
        allocations = tuple(
            (warehouse.warehouse_id, quantity)
            for warehouse, quantity in zip(ordered, quantities)
            if quantity
        )
        cost = sum(
            warehouse.fixed_cost + quantity * warehouse.unit_cost
            for warehouse, quantity in zip(ordered, quantities)
            if quantity
        )
        candidates.append(Solution(cost, allocations))
    return min(candidates, key=lambda item: (item.warehouse_count, item.total_cost, item.allocations), default=None)


class OptimiserTests(unittest.TestCase):
    def test_matches_example(self) -> None:
        warehouses = [
            Warehouse("AU", 5, 8, 2),
            Warehouse("CN", 7, 20, 1),
            Warehouse("US", 4, 3, 4),
        ]
        self.assertEqual(optimise(warehouses, 7), Solution(27, (("CN", 7),)))

    def test_impossible_order(self) -> None:
        self.assertIsNone(optimise([Warehouse("A", 2, 1, 1)], 3))

    def test_zero_stock_is_ignored(self) -> None:
        warehouses = [Warehouse("A", 0, 0, 0), Warehouse("B", 3, 2, 4)]
        self.assertEqual(optimise(warehouses, 2), Solution(10, (("B", 2),)))

    def test_cost_then_lexicographic_tie_break(self) -> None:
        warehouses = [
            Warehouse("A", 2, 1, 1),
            Warehouse("B", 2, 1, 1),
            Warehouse("C", 2, 1, 1),
        ]
        self.assertEqual(optimise(warehouses, 3), Solution(5, (("A", 1), ("B", 2))))

    def test_fewer_warehouses_wins_even_when_more_expensive(self) -> None:
        warehouses = [
            Warehouse("A", 5, 100, 10),
            Warehouse("B", 3, 0, 0),
            Warehouse("C", 2, 0, 0),
        ]
        self.assertEqual(optimise(warehouses, 5), Solution(150, (("A", 5),)))

    def test_random_small_cases_match_exhaustive_search(self) -> None:
        random.seed(7)
        for case in range(100):
            warehouses = [
                Warehouse(chr(65 + index), random.randint(0, 4), random.randint(0, 5), random.randint(0, 5))
                for index in range(random.randint(1, 5))
            ]
            total = sum(warehouse.stock for warehouse in warehouses)
            requested = random.randint(1, max(1, total + 1))
            with self.subTest(case=case, requested=requested, warehouses=warehouses):
                self.assertEqual(optimise(warehouses, requested), brute_force(warehouses, requested))

    def test_large_quantity(self) -> None:
        warehouses = [Warehouse(f"W{index:02}", 2_000, index, index + 1) for index in range(30)]
        solution = optimise(warehouses, 2_000)
        self.assertEqual(solution, Solution(2_000, (("W00", 2_000),)))


if __name__ == "__main__":
    unittest.main()
