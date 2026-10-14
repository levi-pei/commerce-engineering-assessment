# Task B - Fulfilment Split Optimiser

Run from the repository root:

```bash
python -m B.main < input.txt
python -m unittest discover -s B/tests -v
```

Warehouses are processed in ID order. The dynamic programme stores the lowest-cost, lexicographically smallest allocation for each `(warehouses_used, quantity)` state. Warehouse count is selected first by reading the final states from the smallest count upward.

For one warehouse, the transition for quantity `q` considers earlier quantities `t` in `[q-stock, q-1]`. Its variable part is `previous_cost[t] - t * unit_cost`; a monotonic deque finds the best valid `t` in amortised O(1). This avoids enumerating every allocated quantity.

Time complexity is O(W²Q), and space complexity is O(WQ), where W is the warehouse count and Q is the requested quantity. Sorting costs O(W log W).

