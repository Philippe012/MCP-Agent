RATE_CENTS_PER_KG = {
    "standard": 400,
    "express": 900,
}


def round_up_kg(grams: int) -> int:
    # BUG: floor division instead of ceiling - a package that weighs any
    # amount over a whole kilogram (e.g. 1500g) is billed as if it weighed
    # only the whole kilogram below it (1kg), undercharging for the
    # partial kilogram couriers actually bill for.
    if grams <= 0:
        return 0
    return grams // 1000
