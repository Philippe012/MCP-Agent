def load_timeout(config: dict) -> int:
    network = config.get("network", {})
    if "timeout" in network:
        return int(network["timeout"])
    return 30


def load_retries(config: dict) -> int:
    network = config.get("network", {})
    if "retries" in network:
        return int(network["retries"])
    return 3
