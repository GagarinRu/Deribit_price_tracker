beat_schedule = {
    "fetch-prices-every-minute": {
        "task": "src.tasks.periodic_price_fetch",
        "schedule": 60.0,
    },
}
timezone = "UTC"
