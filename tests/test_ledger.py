from ledger.account import Account, Ledger


def _fresh():
    return Ledger([Account("A", 100), Account("B", 50)])


def test_transfer_moves_funds_between_known_accounts():
    ledger = _fresh()
    ledger.transfer("A", "B", 30)
    assert ledger.balance_of("A") == 70
    assert ledger.balance_of("B") == 80


def test_transfer_rejects_insufficient_funds_and_changes_nothing():
    ledger = _fresh()
    try:
        ledger.transfer("A", "B", 1000)
        assert False, "expected ValueError"
    except ValueError:
        pass
    assert ledger.balance_of("A") == 100
    assert ledger.balance_of("B") == 50
