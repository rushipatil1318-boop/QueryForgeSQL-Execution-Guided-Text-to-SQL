"""Create a small original teaching database and deliberately imperfect fixtures."""

import argparse
from pathlib import Path
import sqlite3

from queryforgesql.data import Example, save_dataset, sha256_file, write_json


def prepare_demo(directory: Path):
    if (directory / "manifest.json").exists():
        from queryforgesql.data import verify_manifest
        verify_manifest(directory)
        return
    db_dir = directory / "databases" / "shop"
    db_dir.mkdir(parents=True, exist_ok=True)
    path = db_dir / "shop.sqlite"
    if path.exists():
        raise ValueError("Incomplete demo exists. Use a fresh --output directory")
    with sqlite3.connect(path) as con:
        con.executescript("""
            CREATE TABLE products(id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT NOT NULL);
            CREATE TABLE orders(id INTEGER PRIMARY KEY, ordered_at TEXT NOT NULL);
            CREATE TABLE order_items(order_id INTEGER REFERENCES orders(id),
                product_id INTEGER REFERENCES products(id), quantity INTEGER, unit_price REAL);
            CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT);
        """)
        con.executemany("INSERT INTO products VALUES(?,?,?)", [
            (1,"Notebook","stationery"),(2,"Pen","stationery"),(3,"Backpack","travel"),
            (4,"Bottle","travel"),(5,"Ruler","stationery"),(6,"Pencil","stationery")])
        con.executemany("INSERT INTO orders VALUES(?,?)", [(1,"2026-09-03"),(2,"2026-09-20"),
            (3,"2026-10-02"),(4,"2026-08-31"),(5,"2026-09-30")])
        con.executemany("INSERT INTO order_items VALUES(?,?,?,?)", [
            (1,1,10,5.0),(1,2,20,1.0),(2,3,3,30.0),(2,4,5,10.0),
            (2,5,2,2.0),(3,6,100,2.0),(4,6,100,2.0),(5,1,2,5.0),(5,2,5,1.0)])
        con.executemany("INSERT INTO customers VALUES(?,?)", [(1,"Asha"),(2,"Vikram"),(3,"Mira")])
    revenue = """SELECT p.name, SUM(i.quantity * i.unit_price) AS revenue
        FROM products p JOIN order_items i ON p.id=i.product_id
        JOIN orders o ON o.id=i.order_id
        WHERE o.ordered_at >= '2026-09-01' AND o.ordered_at < '2026-10-01'
        GROUP BY p.id, p.name ORDER BY revenue DESC, p.name ASC LIMIT 5"""
    examples = [
        Example("demo_revenue", "shop", "Which five products generated the highest revenue last month? Return product name and revenue, highest revenue first; break ties by name.", revenue,
                "Revenue is quantity times unit_price. reference_date is 2026-10-30.", "moderate", "2026-10-30"),
        Example("demo_count", "shop", "How many distinct orders are there?", "SELECT COUNT(*) FROM orders", difficulty="simple"),
        Example("demo_invalid", "shop", "List all customer names alphabetically.", "SELECT name FROM customers ORDER BY name", difficulty="simple"),
        Example("demo_semantic", "shop", "Which product names are in the stationery category? Sort alphabetically.", "SELECT name FROM products WHERE category='stationery' ORDER BY name", difficulty="simple"),
        Example("demo_empty", "shop", "List product names whose category is furniture.", "SELECT name FROM products WHERE category='furniture'", difficulty="simple"),
        Example("demo_exhaust", "shop", "What is the total quantity sold, across all order items?", "SELECT SUM(quantity) FROM order_items", difficulty="moderate"),
    ]
    fixtures = {
        "demo_revenue": [revenue.replace("unit_price", "price"), revenue],
        "demo_count": ["SELECT COUNT(*) FROM orders"],
        "demo_invalid": ["DELETE FROM customers", "SELECT name FROM customers ORDER BY name"],
        # This EXECUTES but is semantically wrong. The repair loop must NOT see gold.
        "demo_semantic": ["SELECT name FROM products WHERE category='travel' ORDER BY name"],
        "demo_empty": ["SELECT name FROM products WHERE category='furniture'"],
        "demo_exhaust": ["SELECT missing_quantity FROM order_items"] * 3,
    }
    write_json(directory / "fixture_responses.json", fixtures)
    save_dataset(directory, examples, {"kind": "original_teaching_fixture", "is_bird": False,
        "note": "Scripted model responses; no LLM quality claim"}, 42, {"shop": sha256_file(path)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/demo"))
    args = parser.parse_args()
    prepare_demo(args.output)
    print(f"Teaching fixture ready: {args.output}. This is not BIRD or an LLM benchmark.")


if __name__ == "__main__":
    main()
