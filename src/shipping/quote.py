from shipping.rates import RATE_CENTS_PER_KG, round_up_kg


def quote_cents(service: str, weight_grams: int) -> int:
    if service not in RATE_CENTS_PER_KG:
        raise ValueError(f"unknown service {service!r}")
    kg = round_up_kg(weight_grams)
    return kg * RATE_CENTS_PER_KG[service]
