"""Generate mock cross-border order data for GaussDB."""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

STATUSES = ["awaiting_fulfillment", "picking", "in_transit", "delivered", "exception"]
CHANNELS = ["Amazon US", "Amazon JP", "Shopee", "Lazada", "Shopify", "自营官网"]
DESTINATIONS = ["US", "JP", "DE", "FR", "AE", "SG", "BR", "AU"]
PRODUCTS = [
    "智能筋膜枪",
    "旅行咖啡机",
    "4K 运动相机",
    "家用筋膜枪",
    "折叠跑步机",
    "空气炸锅",
    "睡眠眼罩",
    "登机箱",
    "宠物饮水机",
    "蓝牙耳机",
]
OWNERS = ["ops-us", "ops-cn", "ops-eu", "ops-apac", "ops-latam"]
CUR_MAP = {"US": "USD", "JP": "JPY", "DE": "EUR", "FR": "EUR", "AE": "AED", "SG": "SGD", "BR": "BRL", "AU": "AUD"}

rows = []
now = datetime(2025, 1, 15, 8, 0, 0)
random.seed(42)
for idx in range(1, 101):
    destination = random.choice(DESTINATIONS)
    currency = CUR_MAP[destination]
    channel = random.choice(CHANNELS)
    product = random.choice(PRODUCTS)
    status = random.choices(STATUSES, weights=[4, 3, 4, 5, 1])[0]
    amount = round(random.uniform(49, 1299), 2)
    order_date = now - timedelta(days=random.randint(0, 60), hours=random.randint(0, 20))
    rows.append(
        {
            "title": product,
            "description": f"{destination} · {channel}",
            "status": status,
            "priority": random.randint(1, 5),
            "owner": random.choice(OWNERS),
            "order_number": f"ORD-2025-{idx:04d}",
            "sales_channel": channel,
            "destination_market": destination,
            "currency": currency,
            "order_amount": amount,
            "tracking_number": f"PKG{idx:05d}{destination}",
            "order_date": order_date.isoformat(timespec="seconds"),
        }
    )

path = Path("data/orders_seed.csv")
path.parent.mkdir(parents=True, exist_ok=True)
with path.open("w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(f"Generated {len(rows)} rows -> {path}")
