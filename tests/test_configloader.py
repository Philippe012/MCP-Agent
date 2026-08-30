from configloader.loader import load_retries, load_timeout


def test_nested_config_is_read_correctly():
    config = {"network": {"timeout": 45, "retries": 5}}
    assert load_timeout(config) == 45
    assert load_retries(config) == 5


def test_missing_config_returns_documented_defaults():
    assert load_timeout({}) == 30
    assert load_retries({}) == 3
