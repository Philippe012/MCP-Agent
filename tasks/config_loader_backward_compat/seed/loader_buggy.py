def load_timeout(config: dict) -> int:
    # Only looks under "network" - a legacy flat config's top-level
    # "timeout" key is silently ignored and the default is returned
    # instead, with no error to signal anything went wrong.
    network = config.get("network", {})
    if "timeout" in network:
        return int(network["timeout"])
    return 30


def load_retries(config: dict) -> int:
    network = config.get("network", {})
    if "retries" in network:
        return int(network["retries"])
    return 3
