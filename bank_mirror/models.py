"""Bank Mirror data models."""
from dataclasses import dataclass, asdict
from typing import Optional, List
import time
from blockchain.utils import generate_transaction_id


@dataclass
class BankTransaction:
    transaction_id: str
    timestamp: float
    from_account: str
    to_account: Optional[str]
    amount: float
    type: str
    status: str = 'pending'
    node_url: Optional[str] = None

    @classmethod
    def create_deposit(cls, from_account: str, amount: float) -> 'BankTransaction':
        return cls(
            transaction_id=generate_transaction_id(),
            timestamp=time.time(),
            from_account=from_account,
            to_account=None,
            amount=amount,
            type='deposit'
        )

    @classmethod
    def create_withdrawal(cls, from_account: str, amount: float) -> 'BankTransaction':
        return cls(
            transaction_id=generate_transaction_id(),
            timestamp=time.time(),
            from_account=from_account,
            to_account=None,
            amount=amount,
            type='withdrawal'
        )

    @classmethod
    def create_transfer(cls, from_account: str, to_account: str, amount: float) -> 'BankTransaction':
        return cls(
            transaction_id=generate_transaction_id(),
            timestamp=time.time(),
            from_account=from_account,
            to_account=to_account,
            amount=amount,
            type='transfer'
        )

    def to_dict(self) -> dict:
        return asdict(self)

    def to_blockchain_format(self) -> dict:
        return {
            'from_account': self.from_account,
            'to_account': self.to_account,
            'amount': self.amount,
            'type': self.type,
            'transaction_id': self.transaction_id
        }


@dataclass
class BankAccount:
    account_id: str
    balance: float = 0.0
    created_at: float = 0.0

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class TransactionHistory:
    def __init__(self):
        self.transactions: List[BankTransaction] = []

    def add(self, transaction: BankTransaction):
        self.transactions.append(transaction)

    def get_all(self) -> List[dict]:
        return [tx.to_dict() for tx in self.transactions]

    def get_by_account(self, account_id: str) -> List[dict]:
        return [
            tx.to_dict() for tx in self.transactions
            if tx.from_account == account_id or tx.to_account == account_id
        ]

    def get_pending(self) -> List[dict]:
        return [tx.to_dict() for tx in self.transactions if tx.status == 'pending']

    def get_confirmed(self) -> List[dict]:
        return [tx.to_dict() for tx in self.transactions if tx.status == 'confirmed']