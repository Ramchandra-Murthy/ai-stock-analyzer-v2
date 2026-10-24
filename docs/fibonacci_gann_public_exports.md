# Public Gann division helper imports

The Fibonacci-Gann package exports explicit price-range and bar-position division helpers:

```python
from modules.fibonacci_gann import gann_price_divisions, gann_time_divisions

price_levels = gann_price_divisions(80, 160)
time_positions = gann_time_divisions(0, 80)
```

Both functions default to eight equal divisions and return mappings keyed by fractional interval from `0.0` through `1.0`, including both endpoints. The price helper divides a caller-supplied price range; the time helper divides caller-supplied bar positions. Descending intervals preserve the supplied endpoint order.

These exports are convenience imports for the existing deterministic helpers. They do not infer anchors, fetch market data, generate signals, or establish predictive value. Validate input data and any trading hypothesis separately.
