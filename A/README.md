# Task A - Inventory Reservation Ledger

Run from the repository root:

```bash
python -m A.main < input.txt
python -m unittest discover -s A/tests -v
```

Each valid event ID is recorded after its first attempt, including a rejected business operation. A malformed line is rejected without state changes and is not recorded because its event identity cannot be trusted.

All state transitions and duplicate checks are O(1) average time. Final sorting is O(R log R), where R is the number of open reservations. Memory usage is O(E + R) for processed event IDs and open orders.

