"""
Generates realistic synthetic e-commerce data for the RetailPulse project.
Designed to have real analytical patterns baked in:
 - Seasonality (Nov/Dec spike)
 - Customer churn (some customers stop ordering after a point)
 - VIP customers who order frequently (for RFM/cohort analysis to be interesting)
 - Realistic category/price structure
 - A % of cancelled/returned orders
"""

import random
import sqlite3
from datetime import date, timedelta
import pandas as pd

random.seed(42)

START_DATE = date(2023, 1, 1)
END_DATE = date(2025, 6, 30)
TOTAL_DAYS = (END_DATE - START_DATE).days

REGIONS = ["North", "South", "East", "West", "Central"]
CITIES = {
    "North": ["Delhi", "Chandigarh", "Jaipur"],
    "South": ["Bangalore", "Chennai", "Hyderabad"],
    "East": ["Kolkata", "Bhubaneswar", "Patna"],
    "West": ["Mumbai", "Pune", "Ahmedabad"],
    "Central": ["Bhopal", "Nagpur", "Indore"],
}

CATEGORIES = {
    "Electronics": ["Headphones", "Smartphones", "Laptops", "Smartwatches"],
    "Clothing": ["Men's Wear", "Women's Wear", "Kids Wear", "Footwear"],
    "Home & Kitchen": ["Cookware", "Furniture", "Decor", "Appliances"],
    "Beauty": ["Skincare", "Haircare", "Makeup"],
    "Sports": ["Fitness Equipment", "Outdoor Gear", "Sportswear"],
    "Grocery": ["Snacks", "Beverages", "Staples"],
}

FIRST_NAMES = ["Aarav","Vivaan","Aditya","Vihaan","Arjun","Sai","Reyansh","Ayaan","Krishna","Ishaan",
               "Ananya","Diya","Aadhya","Saanvi","Anika","Kiara","Myra","Aarohi","Prisha","Riya",
               "Rohan","Karan","Nikhil","Amit","Sanjay","Priya","Neha","Pooja","Kavya","Sneha"]
LAST_NAMES = ["Sharma","Verma","Gupta","Patel","Kumar","Singh","Reddy","Rao","Nair","Iyer",
              "Mehta","Joshi","Chopra","Malhotra","Kapoor","Bose","Das","Pillai","Menon","Agarwal"]

PAYMENT_METHODS = ["Credit Card", "Debit Card", "UPI", "Net Banking", "Cash on Delivery"]


def random_date(start, days_range):
    return start + timedelta(days=random.randint(0, days_range))


def seasonality_weight(d):
    """Higher order probability in Nov/Dec (festive/holiday season), lower in Feb."""
    if d.month in (11, 12):
        return 2.2
    if d.month == 2:
        return 0.6
    if d.month in (6, 7):
        return 1.3
    return 1.0


def generate_customers(n=2000):
    rows = []
    for cid in range(1, n + 1):
        region = random.choice(REGIONS)
        city = random.choice(CITIES[region])
        first, last = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        signup_offset_days = int(TOTAL_DAYS * (random.random() ** 1.5))  # more customers signed up earlier
        signup_date = START_DATE + timedelta(days=signup_offset_days)
        # Assign a latent "customer type" that drives ordering behavior
        segment_roll = random.random()
        if segment_roll < 0.08:
            segment = "VIP"
        elif segment_roll < 0.55:
            segment = "Returning"
        else:
            segment = "New"
        rows.append({
            "customer_id": cid,
            "first_name": first,
            "last_name": last,
            "email": f"{first.lower()}.{last.lower()}{cid}@example.com",
            "signup_date": signup_date.isoformat(),
            "city": city,
            "region": region,
            "customer_segment": segment,
        })
    return pd.DataFrame(rows)


def generate_stores(n=15):
    rows = []
    for sid in range(1, n + 1):
        region = random.choice(REGIONS)
        store_type = "Online" if random.random() < 0.4 else "Physical"
        rows.append({
            "store_id": sid,
            "store_name": f"{region} {'Online Hub' if store_type == 'Online' else 'Store'} #{sid}",
            "region": region,
            "store_type": store_type,
        })
    return pd.DataFrame(rows)


def generate_products(n=150):
    rows = []
    pid = 1
    for category, subs in CATEGORIES.items():
        for sub in subs:
            count = n // (len(CATEGORIES) * len(subs)) + random.randint(2, 6)
            for _ in range(count):
                cost = round(random.uniform(5, 300), 2)
                margin = random.uniform(1.3, 2.5)
                price = round(cost * margin, 2)
                rows.append({
                    "product_id": pid,
                    "product_name": f"{sub} Model {pid}",
                    "category": category,
                    "sub_category": sub,
                    "unit_cost": cost,
                    "unit_price": price,
                })
                pid += 1
    return pd.DataFrame(rows)


def generate_orders_and_items(customers_df, stores_df, products_df):
    order_rows = []
    item_rows = []
    order_id = 1
    item_id = 1

    store_ids = stores_df["store_id"].tolist()
    product_ids = products_df["product_id"].tolist()
    product_price_map = dict(zip(products_df["product_id"], products_df["unit_price"]))

    # Behavior multipliers per segment (orders per customer, roughly)
    segment_order_count = {"VIP": (25, 60), "Returning": (5, 20), "New": (1, 5)}

    for _, cust in customers_df.iterrows():
        cid = cust["customer_id"]
        segment = cust["customer_segment"]
        signup = date.fromisoformat(cust["signup_date"])
        days_active = (END_DATE - signup).days
        if days_active <= 0:
            continue

        lo, hi = segment_order_count[segment]
        n_orders = random.randint(lo, hi)

        # Some customers churn: they stop ordering after some point (esp. "New" and some "Returning")
        churn_point = days_active
        if segment != "VIP" and random.random() < 0.35:
            churn_point = int(days_active * random.uniform(0.3, 0.8))

        for _ in range(n_orders):
            # weighted random date favoring seasonality
            for _try in range(5):
                offset = random.randint(0, max(churn_point, 1))
                order_date = signup + timedelta(days=offset)
                if order_date > END_DATE:
                    continue
                if random.random() < seasonality_weight(order_date) / 2.5:
                    break

            store_id = random.choice(store_ids)
            status_roll = random.random()
            if status_roll < 0.04:
                status = "Cancelled"
            elif status_roll < 0.09:
                status = "Returned"
            else:
                status = "Completed"

            order_rows.append({
                "order_id": order_id,
                "customer_id": cid,
                "store_id": store_id,
                "order_date": order_date.isoformat(),
                "order_status": status,
                "payment_method": random.choice(PAYMENT_METHODS),
            })

            n_items = random.randint(1, 4)
            chosen_products = random.sample(product_ids, min(n_items, len(product_ids)))
            for pid in chosen_products:
                qty = random.randint(1, 3)
                price = product_price_map[pid]
                discount = random.choice([0, 0, 0, 5, 10, 15, 20])
                item_rows.append({
                    "order_item_id": item_id,
                    "order_id": order_id,
                    "product_id": pid,
                    "quantity": qty,
                    "unit_price": price,
                    "discount_pct": discount,
                })
                item_id += 1

            order_id += 1

    return pd.DataFrame(order_rows), pd.DataFrame(item_rows)


def main():
    print("Generating customers...")
    customers = generate_customers(2000)
    print("Generating stores...")
    stores = generate_stores(15)
    print("Generating products...")
    products = generate_products(150)
    print("Generating orders and order items (this creates the bulk of the data)...")
    orders, order_items = generate_orders_and_items(customers, stores, products)

    print(f"\nGenerated:")
    print(f"  Customers:    {len(customers):,}")
    print(f"  Stores:       {len(stores):,}")
    print(f"  Products:     {len(products):,}")
    print(f"  Orders:       {len(orders):,}")
    print(f"  Order Items:  {len(order_items):,}")

    customers.to_csv("customers.csv", index=False)
    stores.to_csv("stores.csv", index=False)
    products.to_csv("products.csv", index=False)
    orders.to_csv("orders.csv", index=False)
    order_items.to_csv("order_items.csv", index=False)
    print("\nCSV files written to current directory.")


if __name__ == "__main__":
    main()
