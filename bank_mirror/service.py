"""Bank Mirror service for generating and sending transactions."""
import logging
import requests
import threading
import time
from typing import List, Optional, Dict, Any
from bank_mirror.models import BankTransaction, BankAccount, TransactionHistory


logger = logging.getLogger(__name__)


class BankMirrorService:
    def __init__(self, blockchain_nodes: List[str]):
        self.blockchain_nodes = blockchain_nodes
        self.accounts: Dict[str, BankAccount] = {}
        self.history = TransactionHistory()
        self.current_node_index = 0
        self._lock = threading.Lock()

    def add_node(self, node_url: str):
        with self._lock:
            if node_url not in self.blockchain_nodes:
                self.blockchain_nodes.append(node_url)
                logger.info(f"Added blockchain node: {node_url}")

    def remove_node(self, node_url: str):
        with self._lock:
            if node_url in self.blockchain_nodes:
                self.blockchain_nodes.remove(node_url)
                logger.info(f"Removed blockchain node: {node_url}")

    def get_next_node(self) -> Optional[str]:
        with self._lock:
            if not self.blockchain_nodes:
                return None
            node = self.blockchain_nodes[self.current_node_index]
            self.current_node_index = (self.current_node_index + 1) % len(self.blockchain_nodes)
            return node

    def create_account(self, account_id: str, initial_balance: float = 0.0) -> BankAccount:
        account = BankAccount(account_id=account_id, balance=initial_balance)
        self.accounts[account_id] = account
        logger.info(f"Account created: {account_id} with balance {initial_balance}")
        return account

    def get_account(self, account_id: str) -> Optional[BankAccount]:
        return self.accounts.get(account_id)

    def send_transaction(self, transaction: BankTransaction) -> Dict[str, Any]:
        node_url = self.get_next_node()
        if not node_url:
            return {'success': False, 'error': 'No blockchain nodes available'}

        try:
            response = requests.post(
                f"{node_url}/transactions/new",
                json=transaction.to_blockchain_format(),
                timeout=5
            )
            
            if response.status_code == 201:
                transaction.status = 'pending'
                transaction.node_url = node_url
                self.history.add(transaction)
                logger.info(f"Transaction sent to {node_url}: {transaction.transaction_id}")
                return {'success': True, 'transaction': transaction.to_dict(), 'node': node_url}
            else:
                return {'success': False, 'error': f"Node returned {response.status_code}", 'details': response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send transaction to {node_url}: {e}")
            return {'success': False, 'error': str(e)}

    def deposit(self, from_account: str, amount: float) -> Dict[str, Any]:
        if from_account not in self.accounts:
            self.create_account(from_account)
        
        transaction = BankTransaction.create_deposit(from_account, amount)
        return self.send_transaction(transaction)

    def withdrawal(self, from_account: str, amount: float) -> Dict[str, Any]:
        if from_account not in self.accounts:
            return {'success': False, 'error': f'Account {from_account} does not exist'}
        
        if self.accounts[from_account].balance < amount:
            return {'success': False, 'error': 'Insufficient balance'}
        
        transaction = BankTransaction.create_withdrawal(from_account, amount)
        return self.send_transaction(transaction)

    def transfer(self, from_account: str, to_account: str, amount: float) -> Dict[str, Any]:
        if from_account not in self.accounts:
            return {'success': False, 'error': f'Source account {from_account} does not exist'}
        
        if to_account not in self.accounts:
            self.create_account(to_account)
        
        if self.accounts[from_account].balance < amount:
            return {'success': False, 'error': 'Insufficient balance'}
        
        transaction = BankTransaction.create_transfer(from_account, to_account, amount)
        return self.send_transaction(transaction)

    def custom_transaction(self, from_account: str, to_account: Optional[str], amount: float, tx_type: str) -> Dict[str, Any]:
        if tx_type not in ('deposit', 'withdrawal', 'transfer'):
            return {'success': False, 'error': 'Invalid transaction type'}
        
        if tx_type == 'transfer' and not to_account:
            return {'success': False, 'error': 'Transfer requires destination account'}
        
        if from_account not in self.accounts:
            self.create_account(from_account)
        
        if to_account and to_account not in self.accounts:
            self.create_account(to_account)
        
        if tx_type == 'deposit':
            transaction = BankTransaction.create_deposit(from_account, amount)
        elif tx_type == 'withdrawal':
            transaction = BankTransaction.create_withdrawal(from_account, amount)
        else:
            if not to_account:
                return {'success': False, 'error': 'Transfer requires destination account'}
            transaction = BankTransaction.create_transfer(from_account, to_account, amount)
        
        return self.send_transaction(transaction)

    def get_status(self) -> Dict[str, Any]:
        return {
            'nodes': self.blockchain_nodes,
            'accounts': {k: {'balance': v.balance} for k, v in self.accounts.items()},
            'pending_transactions': len(self.history.get_pending()),
            'total_transactions': len(self.history.transactions)
        }

    def get_history(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        if account_id:
            transactions = self.history.get_by_account(account_id)
        else:
            transactions = self.history.get_all()
        
        return {
            'success': True,
            'transactions': transactions,
            'count': len(transactions)
        }