from services.valuation.comparable.statistics import compute_statistics

# Peer EV/EBITDA multiples with an outlier (31.7x)
multiples = [16.5, 17.2, 17.9, 18.4, 19.2, 31.7]

stats = compute_statistics(multiples)

print(f"Count        : {stats.count}")
print(f"Mean         : {stats.mean:.2f}x")
print(f"Median       : {stats.median:.2f}x")
print(f"Trimmed Mean : {stats.trimmed_mean:.2f}x")
print(f"Std Dev      : {stats.standard_deviation:.2f}x")
print(f"Q1 - Q3      : {stats.q1:.2f}x - {stats.q3:.2f}x (IQR: {stats.iqr:.2f}x)")
print(f"Outliers     : {stats.outliers}")
