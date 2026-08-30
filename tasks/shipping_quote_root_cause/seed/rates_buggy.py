RATE_CENTS_PER_KG = {
    "standard": 400,
    "express": 900,
}


def round_up_kg(grams: int) -> int:
    if grams <= 0:
        return 0
    return grams // 1000
