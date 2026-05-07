import csv

CHAIN_BLOCKLIST = {
    "mcdonald's", "mcdonalds", "starbucks", "tim hortons", "blenz",
    "waves coffee", "a&w", "subway", "second cup", "7-eleven",
    "shell", "esso",
}


def is_chain(name: str) -> bool:
    n = name.lower().strip()
    return any(chain in n for chain in CHAIN_BLOCKLIST)


with open("cafes.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

kept = [r for r in rows if not is_chain(r["name"])]
removed = [r for r in rows if is_chain(r["name"])]

print(f"Kept: {len(kept)}")
print(f"Removed: {len(removed)}")
for r in removed:
    print(f"  - {r['name']}")

# write cleaned file
with open("cafes_cleaned.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(kept)

print("\nWrote cafes_cleaned.csv")