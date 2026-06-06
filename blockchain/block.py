"""Block model for the blockchain."""
import json
import time
from typing import Any, Dict, List, Optional
from blockchain.utils import sha256, hash_block, get_timestamp


class Block:
    def __init__(
        self,
        index: int,
        timestamp: float,
        transactions: List[Dict[str, Any]],
        proof: int,
        previous_hash: str,
        hash: Optional[str] = None
    ):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.proof = proof
        self.previous_hash = previous_hash
        self.hash = hash or self.compute_hash()

    def compute_hash(self) -> str:
        block_data = {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'proof': self.proof,
            'previous_hash': self.previous_hash
        }
        return hash_block(block_data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'index': self.index,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'proof': self.proof,
            'previous_hash': self.previous_hash,
            'hash': self.hash
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        return cls(
            index=data['index'],
            timestamp=data['timestamp'],
            transactions=data['transactions'],
            proof=data['proof'],
            previous_hash=data['previous_hash'],
            hash=data.get('hash')
        )

    def __repr__(self) -> str:
        return f"Block(index={self.index}, hash={self.hash[:16]}..., tx_count={len(self.transactions)})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Block):
            return False
        return self.hash == other.hash