def load_timeout(config: dict) -> int:
    """Return the network timeout (seconds) from a config dict.

    Supports both the legacy flat shape (`{"timeout": N}`) and the current
    nested shape (`{"network": {"timeout": N}}`). New configs should use
    the nested shape, but old configs written before that change must keep
    working unchanged. If both are present, the nested value wins.
    """
    network = config.get("network")
    if isinstance(network, dict) and "timeout" in network:
        return int(network["timeout"])
    if "timeout" in config:
        return int(config["timeout"])
    return 30


def load_retries(config: dict) -> int:
    """Same backward-compatibility contract as load_timeout, for retries."""
    network = config.get("network")
    if isinstance(network, dict) and "retries" in network:
        return int(network["retries"])
    if "retries" in config:
        return int(config["retries"])
    return 3
