from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Result:
    status: str
    on_hand: int
    reserved: int

    def render(self) -> str:
        return f"{self.status} {self.on_hand} {self.reserved}"


@dataclass
class InventoryLedger:
    on_hand: int
    reservations: dict[str, int] = field(default_factory=dict)
    processed_events: set[str] = field(default_factory=set)
    _reserved_total: int = 0

    def __post_init__(self) -> None:
        if self.on_hand < 0:
            raise ValueError("initial stock must be non-negative")

    @property
    def reserved(self) -> int:
        return self._reserved_total

    @property
    def available(self) -> int:
        return self.on_hand - self._reserved_total

    def process_line(self, line: str) -> Result:
        parsed = self._parse(line)
        if parsed is None:
            # 格式错误的输入没有可信的事件标识；即使包含令牌，也不能记录为幂等事件。
            return self._result("REJECTED")

        command, event_id, order_id, quantity = parsed
        if event_id in self.processed_events:
            return self._result("DUPLICATE")

        accepted = self._apply(command, order_id, quantity)
        # 语法正确的事件即使未通过业务规则，也视为已处理，确保重放时幂等。
        self.processed_events.add(event_id)
        return self._result("OK" if accepted else "REJECTED")

    def open_reservations(self) -> list[tuple[str, int]]:
        return sorted(self.reservations.items())

    def _apply(self, command: str, order_id: str | None, quantity: int) -> bool:
        if command == "RESTOCK":
            self.on_hand += quantity
            return True

        assert order_id is not None
        current = self.reservations.get(order_id, 0)

        if command == "RESERVE":
            # 预留会立即减少可用库存；只有发货时才会减少实际在库数量。
            if quantity > self.available:
                return False
            self.reservations[order_id] = current + quantity
            self._reserved_total += quantity
            return True

        if quantity > current:
            return False

        remaining = current - quantity
        if remaining:
            self.reservations[order_id] = remaining
        else:
            self.reservations.pop(order_id, None)
        self._reserved_total -= quantity

        if command == "SHIP":
            # 发货同时消耗该订单的预留数量和为该预留保留的实际库存。
            self.on_hand -= quantity
        return True

    def _result(self, status: str) -> Result:
        return Result(status, self.on_hand, self._reserved_total)

    @staticmethod
    def _parse(line: str) -> tuple[str, str, str | None, int] | None:
        parts = line.split()
        if not parts:
            return None

        command = parts[0]
        expected = 3 if command == "RESTOCK" else 4
        if command not in {"RESERVE", "RELEASE", "SHIP", "RESTOCK"}:
            return None
        if len(parts) != expected or not all(_is_ascii_token(part) for part in parts):
            return None

        try:
            quantity = int(parts[-1])
        except ValueError:
            return None
        if quantity <= 0 or str(quantity) != parts[-1]:
            return None

        event_id = parts[1]
        order_id = None if command == "RESTOCK" else parts[2]
        return command, event_id, order_id, quantity


def run(initial_stock: int, commands: Iterable[str]) -> list[str]:
    ledger = InventoryLedger(initial_stock)
    output = [ledger.process_line(command).render() for command in commands]
    output.extend(f"OPEN {order_id} {quantity}" for order_id, quantity in ledger.open_reservations())
    if not ledger.reservations:
        output.append("OPEN 0")
    return output


def _is_ascii_token(value: str) -> bool:
    return bool(value) and value.isascii() and not any(character.isspace() for character in value)
