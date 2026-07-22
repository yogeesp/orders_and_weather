"""
event_generator.py
Synthetic e-commerce event generator with weather enrichment.
"""
import logging
import random
import time, uuid
from datetime import datetime, timedelta
from typing import Dict, Tuple
import requests
import json
from pathlib import Path
from faker import Faker


fake = Faker("en_IN")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

INDIAN_CITIES = {
    "Mumbai": (19.0760,72.8777),
    "Delhi": (28.7041,77.1025),
    "Bangalore": (12.9716,77.5946),
    "Chennai": (13.0827,80.2707),
    "Kolkata": (22.5726,88.3639),
    "Hyderabad": (17.3850,78.4867),
}
PRODUCTS = {
    "Electronics":{"price":(200,1800),"qty":(1,2)},
    "Fashion":{"price":(20,150),"qty":(1,5)},
    "Home and Kitchen":{"price":(15,600),"qty":(1,3)},
    "Sports":{"price":(30,350),"qty":(1,2)},
    "Beauty":{"price":(10,120),"qty":(1,3)},
    "Books":{"price":(8,50),"qty":(1,4)},
}
WINDOW_DAYS=15
RECENT_MINUTES=10
TIMEOUT=5
RETRIES=3
API="https://api.open-meteo.com/v1/forecast"

class WeatherClient:
    def __init__(self):
        self.s=requests.Session()
        self.cache:Dict[Tuple[str,str],Tuple[float,float]]={}
    def get_weather(self,city,lat,lon,event_dt):
        hour=event_dt.strftime("%Y-%m-%dT%H:00")
        key=(city,hour)
        if key in self.cache:
            return self.cache[key]
        params={"latitude":lat,"longitude":lon,
                "hourly":"temperature_2m,relative_humidity_2m",
                "start_hour":hour,"end_hour":hour,"timezone":"auto"}
        for _ in range(RETRIES):
            try:
                r=self.s.get(API,params=params,timeout=TIMEOUT)
                r.raise_for_status()
                h=r.json().get("hourly",{})
                if h.get("time"):
                    val=(h["temperature_2m"][0],h["relative_humidity_2m"][0])
                    self.cache[key]=val
                    return val
            except Exception:
                pass
        return (None,None)

weather=WeatherClient()

def generate_event_time():
    x=random.random()
    now=datetime.now()
    if x<0.90:
        return fake.date_time_between(start_date=now-timedelta(minutes=RECENT_MINUTES),end_date=now)
    if x<0.97:
        return now-timedelta(minutes=random.randint(10,60))
    if x<0.99:
        return now-timedelta(hours=random.randint(1,6))
    return now-timedelta(days=random.randint(1,WINDOW_DAYS),hours=random.randint(0,23))

def generate_order():
    city=random.choice(list(INDIAN_CITIES))
    lat,lon=INDIAN_CITIES[city]
    cat=random.choice(list(PRODUCTS))
    p=PRODUCTS[cat]
    qty=random.randint(*p["qty"])
    price=round(random.uniform(*p["price"]),2)
    event_dt=generate_event_time()
    temp,hum=weather.get_weather(city,lat,lon,event_dt)
    return {
        "order_id":uuid.uuid4().hex,
        "user_id":fake.random_int(100000,999999),
        "product_category":cat,
        "quantity":qty,
        "unit_price_usd":price,
        "city":city,
        "country":"India",
        "event_timestamp":event_dt.isoformat(),
        "temperature":temp,
        "humidity":hum
    }

def generate_batch(n=20):
    return [generate_order() for _ in range(n)]

def generate_stream(events_per_second=2):
    delay=1/events_per_second
    while True:
        print(generate_order())
        time.sleep(delay)

def write_json_batch(orders, output_dir, filename=None):
    """
    Writes a batch of orders as newline-delimited JSON (JSONL).
    Each line is one event.
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    file_path = output_path / filename

    with open(file_path, "w") as f:
        for order in orders:
            f.write(json.dumps(order))
            f.write("\n")

    logging.info(f"Wrote {len(orders)} events to {file_path}")
if __name__=="__main__":
    for o in generate_batch(10):
        print(o)
