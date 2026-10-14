import unittest

from A.ledger import InventoryLedger, run


class InventoryLedgerTests(unittest.TestCase):
    def test_matches_example(self) -> None:
        commands = [
            "RESERVE e1 o100 4",
            "RESERVE e2 o200 7",
            "SHIP e3 o100 2",
            "RELEASE e4 o100 2",
            "RESTOCK e5 3",
            "RESERVE e2 o999 1",
        ]
        self.assertEqual(
            run(10, commands),
            [
                "OK 10 4",
                "REJECTED 10 4",
                "OK 8 2",
                "OK 8 0",
                "OK 11 0",
                "DUPLICATE 11 0",
                "OPEN 0",
            ],
        )

    def test_rejected_business_event_is_idempotent(self) -> None:
        ledger = InventoryLedger(1)
        self.assertEqual(ledger.process_line("RESERVE e1 order 2").status, "REJECTED")
        self.assertEqual(ledger.process_line("RESERVE e1 order 1").status, "DUPLICATE")
        self.assertEqual((ledger.on_hand, ledger.reserved), (1, 0))

    def test_malformed_input_never_changes_or_records_state(self) -> None:
        ledger = InventoryLedger(5)
        for line in ["", "RESERVE e1 order", "SHIP e1 order -1", "RESTOCK e1 01", "BOGUS e1 2"]:
            self.assertEqual(ledger.process_line(line).status, "REJECTED")
        self.assertEqual((ledger.on_hand, ledger.reserved, ledger.processed_events), (5, 0, set()))

    def test_release_and_ship_cannot_exceed_order_reservation(self) -> None:
        ledger = InventoryLedger(10)
        ledger.process_line("RESERVE reserve order-a 5")
        self.assertEqual(ledger.process_line("RELEASE release order-b 1").status, "REJECTED")
        self.assertEqual(ledger.process_line("SHIP ship order-a 6").status, "REJECTED")
        self.assertEqual((ledger.on_hand, ledger.reserved), (10, 5))

    def test_ship_reduces_on_hand_and_reserved(self) -> None:
        ledger = InventoryLedger(3)
        ledger.process_line("RESERVE e1 order 3")
        result = ledger.process_line("SHIP e2 order 2")
        self.assertEqual((result.status, result.on_hand, result.reserved), ("OK", 1, 1))

    def test_open_reservations_are_sorted(self) -> None:
        output = run(4, ["RESERVE e1 z 1", "RESERVE e2 a 2"])
        self.assertEqual(output[-2:], ["OPEN a 2", "OPEN z 1"])


if __name__ == "__main__":
    unittest.main()

