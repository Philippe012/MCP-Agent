from configloader.loader import load_retries, load_timeout


def test_legacy_flat_config_is_read_correctly():
    assert load_timeout({"timeout": 45}) == 45
    assert load_retries({"retries": 5}) == 5
