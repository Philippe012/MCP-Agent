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
        """Move `amount` cents from `from_id` to `to_id`. Must be atomic:
        if the destination doesn't exist, the source account must be left
        completely unchanged - a transfer either happens in full or not at
        all, never half."""
        if amount <= 0:
            raise ValueError("transfer amount must be positive")
        source = self.accounts[from_id]
        if source.balance < amount:
            raise ValueError("insufficient funds")
        if to_id not in self.accounts:
            raise KeyError(f"unknown destination account {to_id!r}")
        self.accounts[from_id] = replace(source, balance=source.balance - amount)
        dest = self.accounts[to_id]
        self.accounts[to_id] = replace(dest, balance=dest.balance + amount)
