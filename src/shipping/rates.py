RATE_CENTS_PER_KG = {
    "standard": 400,
    "express": 900,
}


def round_up_kg(grams: int) -> int:
    """Couriers bill for any part of a kilogram as a full kilogram."""
    if grams <= 0:
        return 0
    return -(-grams // 1000)  
