"""API request/response schemas and validation."""
from typing import Any, Dict, Optional
from dataclasses import dataclass


@dataclass
class TransactionRequest:
    from_account: str
    amount: float
    type: str
    to_account: Optional[str] = None
    transaction_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionRequest':
        return cls(
            from_account=data.get('from_account', ''),
            amount=float(data.get('amount', 0)),
            type=data.get('type', ''),
            to_account=data.get('to_account'),
            transaction_id=data.get('transaction_id')
        )

    def validate(self) -> tuple:
        if not self.from_account:
            return False, "from_account is required"
        if self.amount <= 0:
            return False, "amount must be positive"
        if self.type not in ('deposit', 'withdrawal', 'transfer'):
            return False, "type must be deposit, withdrawal, or transfer"
        if self.type == 'transfer' and not self.to_account:
            return False, "to_account is required for transfers"
        return True, None


@dataclass
class NodeRegistrationRequest:
    nodes: list

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NodeRegistrationRequest':
        return cls(nodes=data.get('nodes', []))


@dataclass
class BlockRequest:
    index: int
    timestamp: float
    transactions: list
    proof: int
    previous_hash: str
    hash: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BlockRequest':
        return cls(
            index=data.get('index', 0),
            timestamp=data.get('timestamp', 0),
            transactions=data.get('transactions', []),
            proof=data.get('proof', 0),
            previous_hash=data.get('previous_hash', ''),
            hash=data.get('hash', '')
        )