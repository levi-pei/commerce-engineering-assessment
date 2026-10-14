from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Warehouse:
    warehouse_id: str
    stock: int
    fixed_cost: int
    unit_cost: int


@dataclass(frozen=True)
class Solution:
    total_cost: int
    allocations: tuple[tuple[str, int], ...]

    @property
    def warehouse_count(self) -> int:
        return len(self.allocations)


@dataclass(frozen=True)
class _Candidate:
    cost: int
    allocations: tuple[tuple[str, int], ...]

    @property
    def key(self) -> tuple[int, tuple[tuple[str, int], ...]]:
        return self.cost, self.allocations


def optimise(warehouses: Iterable[Warehouse], requested: int) -> Solution | None:
    if requested < 1:
        raise ValueError("requested quantity must be positive")

    ordered = sorted(warehouses, key=lambda warehouse: warehouse.warehouse_id)
    if len({warehouse.warehouse_id for warehouse in ordered}) != len(ordered):
        raise ValueError("warehouse IDs must be unique")
    if any(
        warehouse.stock < 0 or warehouse.fixed_cost < 0 or warehouse.unit_cost < 0
        for warehouse in ordered
    ):
        raise ValueError("stock and costs must be non-negative")
    if sum(warehouse.stock for warehouse in ordered) < requested:
        return None

    max_used = min(len(ordered), requested)
    # dp[used][quantity] 保存已处理仓库下的最低成本分配方案。
    # 使用元组保存分配结果，使最终的字典序决策明确，而非依赖遍历顺序。
    dp: list[list[_Candidate | None]] = [
        [None] * (requested + 1) for _ in range(max_used + 1)
    ]
    dp[0][0] = _Candidate(0, ())

    for index, warehouse in enumerate(ordered):
        if warehouse.stock == 0:
            continue

        previous = [row[:] for row in dp]
        highest_count = min(index + 1, max_used)
        for used in range(1, highest_count + 1):
            # 当前仓库分配 x 时，前序数量为 t=q-x。
            # 单位成本为线性关系，可在有效 t 窗口中用单调队列最小化
            # cost[t] - t * unit_cost，避免枚举每一种 x。
            window: deque[tuple[int, _Candidate, tuple[int, tuple[tuple[str, int], ...]]]] = deque()
            source = previous[used - 1]

            for quantity in range(1, requested + 1):
                source_quantity = quantity - 1
                source_candidate = source[source_quantity]
                if source_candidate is not None:
                    rank = (
                        source_candidate.cost - source_quantity * warehouse.unit_cost,
                        source_candidate.allocations,
                    )
                    while window and window[-1][2] >= rank:
                        window.pop()
                    window.append((source_quantity, source_candidate, rank))

                minimum_source = quantity - warehouse.stock
                # 小于该边界的状态会使当前仓库的分配量超过自身库存。
                while window and window[0][0] < minimum_source:
                    window.popleft()
                if not window:
                    continue

                base_quantity, base_candidate, _ = window[0]
                allocated = quantity - base_quantity
                candidate = _Candidate(
                    cost=base_candidate.cost + warehouse.fixed_cost + allocated * warehouse.unit_cost,
                    allocations=base_candidate.allocations + ((warehouse.warehouse_id, allocated),),
                )
                existing = dp[used][quantity]
                if existing is None or candidate.key < existing.key:
                    dp[used][quantity] = candidate

    for used in range(1, max_used + 1):
        candidate = dp[used][requested]
        if candidate is not None:
            return Solution(candidate.cost, candidate.allocations)
    return None
