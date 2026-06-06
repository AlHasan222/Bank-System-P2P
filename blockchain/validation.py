"""Validation logic for blocks, transactions, and chains."""
import logging
from typing import Any, Dict, List, Optional, Tuple
from blockchain.block import Block
from blockchain.utils import validate_amount, validate_transaction_type, sha256


logger = logging.getLogger(__name__)


REQUIRED_TRANSACTION_FIELDS = ['from_account', 'amount', 'type']
VALID_TRANSACTION_TYPES = ('deposit', 'withdrawal', 'transfer')


def validate_transaction_structure(transaction: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    if not isinstance(transaction, dict):
        return False, "Transaction must be a dictionary"
    
    for field in REQUIRED_TRANSACTION_FIELDS:
        if field not in transaction:
            return False, f"Missing required field: {field}"
    
    if not validate_transaction_type(transaction['type']):
        return False, f"Invalid transaction type: {transaction['type']}"
    
    if not validate_amount(transaction['amount']):
        return False, "Amount must be a positive number"
    
    tx_type = transaction['type']
    if tx_type == 'transfer':
        if 'to_account' not in transaction or not transaction['to_account']:
            return False, "Transfer requires a destination account"
    elif tx_type in ('deposit', 'withdrawal'):
        if transaction.get('to_account') is not None:
            return False, f"{tx_type.capitalize()} should not have a destination account"
    
    return True, None


def validate_transaction(transaction: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    is_valid, error = validate_transaction_structure(transaction)
    if not is_valid:
        logger.warning(f"Transaction validation failed: {error}")
    return is_valid, error


def validate_block_structure(block: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    required_fields = ['index', 'timestamp', 'transactions', 'proof', 'previous_hash', 'hash']
    for field in required_fields:
        if field not in block:
            return False, f"Block missing required field: {field}"
    
    if not isinstance(block['transactions'], list):
        return False, "Block transactions must be a list"
    
    return True, None


def validate_block(block: Block, previous_block: Optional[Block] = None, difficulty: int = 4) -> Tuple[bool, Optional[str]]:
    if previous_block:
        if block.index != previous_block.index + 1:
            return False, f"Invalid block index: expected {previous_block.index + 1}, got {block.index}"
        
        if block.previous_hash != previous_block.hash:
            return False, f"Previous hash mismatch: expected {previous_block.hash}, got {block.previous_hash}"
    
    computed_hash = block.compute_hash()
    if block.hash != computed_hash:
        return False, f"Block hash mismatch: expected {computed_hash}, got {block.hash}"
    
    # Skip PoW check for genesis block (index 0)
    if block.index > 0:
        if not block.hash.startswith('0' * difficulty):
            return False, f"Invalid proof of work: hash does not meet difficulty {difficulty}"
    
    for tx in block.transactions:
        is_valid, error = validate_transaction(tx)
        if not is_valid:
            return False, f"Invalid transaction in block: {error}"
    
    return True, None


def validate_chain(chain: List[Block], difficulty: int = 4) -> Tuple[bool, List[str]]:
    issues = []
    
    if not chain:
        return False, ["Chain is empty"]
    
    genesis = chain[0]
    if genesis.index != 0:
        issues.append("Genesis block must have index 0")
    
    if genesis.previous_hash != "0":
        issues.append("Genesis block must have previous_hash '0'")
    
    for i, block in enumerate(chain):
        if i > 0:
            is_valid, error = validate_block(block, chain[i - 1], difficulty)
            if not is_valid:
                issues.append(f"Block {block.index}: {error}")
        else:
            is_valid, error = validate_block(block, difficulty=difficulty)
            if not is_valid:
                issues.append(f"Genesis block: {error}")
    
    return len(issues) == 0, issues


def validate_pending_transactions(transactions: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    issues = []
    for i, tx in enumerate(transactions):
        is_valid, error = validate_transaction(tx)
        if not is_valid:
            issues.append(f"Transaction {i}: {error}")
    return len(issues) == 0, issues