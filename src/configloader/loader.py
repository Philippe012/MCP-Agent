def load_timeout(config: dict) -> int:
    
    network = config.get("network")
    if isinstance(network, dict) and "timeout" in network:
        return int(network["timeout"])
    if "timeout" in config:
        return int(config["timeout"])
    return 30


def load_retries(config: dict) -> int:
    network = config.get("network")
    if isinstance(network, dict) and "retries" in network:
        return int(network["retries"])
    if "retries" in config:
        return int(config["retries"])
    return 3
