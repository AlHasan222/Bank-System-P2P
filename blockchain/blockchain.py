"""Core blockchain implementation."""
import logging
import json
from typing import Any, Dict, List, Optional, Set
from blockchain.block import Block
from blockchain.validation import (
    validate_transaction,
    validate_block,
    validate_chain,
    validate_pending_transactions
)
from blockchain.utils import sha256, get_timestamp, generate_transaction_id
from blockchain.config import Config


logger = logging.getLogger(__name__)


class Blockchain:
    def __init__(self, difficulty: int = Config.POW_DIFFICULTY):
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict[str, Any]] = []
        self.difficulty = difficulty
        self.nodes: Set[str] = set()

    def create_genesis_block(self) -> Block:
        genesis_block = Block(
            index=0,
            timestamp=get_timestamp(),
            transactions=[],
            proof=1,
            previous_hash="0"
        )
        self.chain.append(genesis_block)
        logger.info("Genesis block created")
        return genesis_block

    def new_transaction(
        self,
        from_account: str,
        amount: float,
        tx_type: str,
        to_account: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        transaction = {
            'transaction_id': transaction_id or generate_transaction_id(),
            'timestamp': get_timestamp(),
            'from_account': from_account,
            'to_account': to_account,
            'amount': float(amount),
            'type': tx_type
        }
        
        is_valid, error = validate_transaction(transaction)
        if not is_valid:
            raise ValueError(f"Invalid transaction: {error}")
        
        self.pending_transactions.append(transaction)
        logger.info(f"Transaction added to pending pool: {transaction['transaction_id']}")
        return transaction

    def new_block(self, proof: int, timestamp: float, previous_hash: Optional[str] = None) -> Block:
        last_block = self.last_block()
        if not last_block:
            raise RuntimeError("Cannot create block: no genesis block exists")
        block = Block(
            index=len(self.chain),
            timestamp=timestamp,
            transactions=self.pending_transactions.copy(),
            proof=proof,
            previous_hash=previous_hash or last_block.hash
        )
        
        self.pending_transactions = []
        self.chain.append(block)
        logger.info(f"New block mined: index={block.index}, hash={block.hash[:16]}...")
        return block

    def last_block(self) -> Optional[Block]:
        return self.chain[-1] if self.chain else None

    def proof_of_work(self, last_proof: int, transactions: Optional[List[Dict[str, Any]]] = None, previous_hash: Optional[str] = None) -> tuple:
        if transactions is None:
            transactions = self.pending_transactions
        if previous_hash is None:
            last_block = self.last_block()
            previous_hash = last_block.hash if last_block else "0"
        
        proof = 0
        max_iterations = Config.POW_MAX_ITERATIONS
        index = len(self.chain)
        timestamp = get_timestamp()
        
        while proof < max_iterations:
            block = Block(
                index=index,
                timestamp=timestamp,
                transactions=transactions,
                proof=proof,
                previous_hash=previous_hash
            )
            if block.hash.startswith('0' * self.difficulty):
                logger.info(f"Proof of work found: {proof}")
                return proof, timestamp
            proof += 1
        
        raise RuntimeError("Proof of work failed: max iterations reached")

    def valid_proof(self, last_proof: int, proof: int, transactions: Optional[List[Dict[str, Any]]] = None, previous_hash: Optional[str] = None, index: Optional[int] = None, timestamp: Optional[float] = None) -> bool:
        if transactions is None:
            transactions = self.pending_transactions
        if previous_hash is None:
            last_block = self.last_block()
            previous_hash = last_block.hash if last_block else "0"
        if index is None:
            index = len(self.chain)
        if timestamp is None:
            timestamp = get_timestamp()
            
        block = Block(
            index=index,
            timestamp=timestamp,
            transactions=transactions,
            proof=proof,
            previous_hash=previous_hash
        )
        return block.hash.startswith('0' * self.difficulty)

    def valid_chain(self, chain: List[Block]) -> bool:
        is_valid, issues = validate_chain(chain, self.difficulty)
        if not is_valid:
            logger.warning(f"Chain validation failed: {issues}")
        return is_valid

    def resolve_conflicts(self) -> bool:
        if not self.nodes:
            return False
        
        max_length = len(self.chain)
        new_chain = None
        
        for node in self.nodes:
            try:
                response = __import__('requests').get(
                    f"{node}/chain",
                    timeout=Config.NODE_TIMEOUT
                )
                if response.status_code == 200:
                    data = response.json()
                    chain_data = data.get('chain', [])
                    length = data.get('length', 0)
                    
                    if length > max_length:
                        chain = [Block.from_dict(b) for b in chain_data]
                        if self.valid_chain(chain):
                            max_length = length
                            new_chain = chain
                            logger.info(f"Found longer valid chain from {node}: length={length}")
            except Exception as e:
                logger.warning(f"Failed to fetch chain from {node}: {e}")
        
        if new_chain:
            self.chain = new_chain
            logger.info("Chain replaced with longer valid chain")
            return True
        
        return False

    def register_node(self, address: str) -> bool:
        from blockchain.utils import parse_node_url
        parsed = parse_node_url(address)
        if parsed:
            self.nodes.add(parsed)
            logger.info(f"Node registered: {parsed}")
            return True
        return False

    def get_block(self, index: int) -> Optional[Block]:
        if 0 <= index < len(self.chain):
            return self.chain[index]
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'chain': [block.to_dict() for block in self.chain],
            'pending_transactions': self.pending_transactions,
            'difficulty': self.difficulty,
            'nodes': list(self.nodes)
        }

    def get_chain_info(self) -> Dict[str, Any]:
        last = self.last_block()
        return {
            'length': len(self.chain),
            'last_block_hash': last.hash if last else None,
            'pending_count': len(self.pending_transactions),
            'difficulty': self.difficulty,
            'nodes': list(self.nodes)
        }