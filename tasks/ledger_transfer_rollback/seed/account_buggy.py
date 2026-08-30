from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Account:
    account_id: str
    balance: int  # integer cents - avoids float rounding noise in a ledger


class Ledger:
    def __init__(self, accounts: list[Account]) -> None:
        self.accounts = {a.account_id: a for a in accounts}

    def balance_of(self, account_id: str) -> int:
        return self.accounts[account_id].balance

    def total_balance(self) -> int:
        return sum(a.balance for a in self.accounts.values())

    def transfer(self, from_id: str, to_id: str, amount: int) -> None:
        if amount <= 0:
            raise ValueError("transfer amount must be positive")
        source = self.accounts[from_id]
        if source.balance < amount:
            raise ValueError("insufficient funds")
        # Debits the source before checking the destination exists - if
        # to_id is unknown, the KeyError below fires *after* the source has
        # already been decremented, and the funds are gone with no matching
        # credit anywhere.
        self.accounts[from_id] = replace(source, balance=source.balance - amount)
        dest = self.accounts[to_id]
        self.accounts[to_id] = replace(dest, balance=dest.balance + amount)
