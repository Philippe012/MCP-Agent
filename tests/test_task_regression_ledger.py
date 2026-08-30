from ledger.account import Account, Ledger


def test_failed_transfer_to_unknown_account_leaves_balances_unchanged():
    ledger = Ledger([Account("A", 100), Account("B", 50)])
    try:
        ledger.transfer("A", "ZZZ", 10)
        assert False, "expected KeyError"
    except KeyError:
        pass
    assert ledger.balance_of("A") == 100
    assert ledger.total_balance() == 150
