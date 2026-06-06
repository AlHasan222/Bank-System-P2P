"""SQLite persistence layer for blockchain data."""
import sqlite3
import json
import logging
import os
from typing import Any, Dict, List, Optional
from blockchain.block import Block
from blockchain.blockchain import Blockchain
from blockchain.config import Config


logger = logging.getLogger(__name__)


class BlockchainStorage:
    def __init__(self, db_path: str = Config.BLOCKCHAIN_DB_PATH):
        self.db_path = db_path
        self._ensure_data_dir()
        self._init_db()

    def _ensure_data_dir(self):
        data_dir = os.path.dirname(self.db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS blocks (
                    block_index INTEGER PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    transactions TEXT NOT NULL,
                    proof INTEGER NOT NULL,
                    previous_hash TEXT NOT NULL,
                    hash TEXT NOT NULL UNIQUE
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pending_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_id TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    from_account TEXT NOT NULL,
                    to_account TEXT,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nodes (
                    url TEXT PRIMARY KEY
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')
            
            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def save_chain(self, chain: List[Block]) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM blocks')
                
                for block in chain:
                    cursor.execute('''
                        INSERT INTO blocks (block_index, timestamp, transactions, proof, previous_hash, hash)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        block.index,
                        block.timestamp,
                        json.dumps(block.transactions),
                        block.proof,
                        block.previous_hash,
                        block.hash
                    ))
                conn.commit()
            logger.info(f"Chain saved: {len(chain)} blocks")
            return True
        except Exception as e:
            logger.error(f"Failed to save chain: {e}")
            return False

    def load_chain(self) -> List[Block]:
        chain = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM blocks ORDER BY block_index')
                rows = cursor.fetchall()
                
                for row in rows:
                    block = Block(
                        index=row[0],
                        timestamp=row[1],
                        transactions=json.loads(row[2]),
                        proof=row[3],
                        previous_hash=row[4],
                        hash=row[5]
                    )
                    chain.append(block)
            
            logger.info(f"Chain loaded: {len(chain)} blocks")
            return chain
        except Exception as e:
            logger.error(f"Failed to load chain: {e}")
            return []

    def save_pending_transactions(self, transactions: List[Dict[str, Any]]) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM pending_transactions')
                
                for tx in transactions:
                    cursor.execute('''
                        INSERT INTO pending_transactions (transaction_id, timestamp, from_account, to_account, amount, type)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        tx.get('transaction_id', ''),
                        tx.get('timestamp', 0),
                        tx.get('from_account', ''),
                        tx.get('to_account'),
                        tx.get('amount', 0),
                        tx.get('type', '')
                    ))
                conn.commit()
            logger.info(f"Pending transactions saved: {len(transactions)}")
            return True
        except Exception as e:
            logger.error(f"Failed to save pending transactions: {e}")
            return False

    def load_pending_transactions(self) -> List[Dict[str, Any]]:
        transactions = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM pending_transactions ORDER BY id')
                rows = cursor.fetchall()
                
                for row in rows:
                    tx = {
                        'transaction_id': row[1],
                        'timestamp': row[2],
                        'from_account': row[3],
                        'to_account': row[4],
                        'amount': row[5],
                        'type': row[6]
                    }
                    transactions.append(tx)
            
            logger.info(f"Pending transactions loaded: {len(transactions)}")
            return transactions
        except Exception as e:
            logger.error(f"Failed to load pending transactions: {e}")
            return []

    def save_nodes(self, nodes: set) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM nodes')
                
                for node in nodes:
                    cursor.execute('INSERT OR IGNORE INTO nodes (url) VALUES (?)', (node,))
                conn.commit()
            logger.info(f"Nodes saved: {len(nodes)}")
            return True
        except Exception as e:
            logger.error(f"Failed to save nodes: {e}")
            return False

    def load_nodes(self) -> set:
        nodes = set()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT url FROM nodes')
                rows = cursor.fetchall()
                nodes = {row[0] for row in rows}
            
            logger.info(f"Nodes loaded: {len(nodes)}")
            return nodes
        except Exception as e:
            logger.error(f"Failed to load nodes: {e}")
            return set()

    def save_config(self, key: str, value: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)
                ''', (key, value))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save config {key}: {e}")
            return False

    def load_config(self, key: str, default: str = '') -> str:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT value FROM config WHERE key = ?', (key,))
                row = cursor.fetchone()
                return row[0] if row else default
        except Exception as e:
            logger.error(f"Failed to load config {key}: {e}")
            return default

    def initialize_blockchain(self, blockchain: Blockchain) -> bool:
        chain = self.load_chain()
        
        if chain:
            blockchain.chain = chain
            logger.info("Blockchain loaded from storage")
        else:
            blockchain.create_genesis_block()
            self.save_chain(blockchain.chain)
            logger.info("New blockchain initialized with genesis block")
        
        blockchain.pending_transactions = self.load_pending_transactions()
        blockchain.nodes = self.load_nodes()
        
        # Load difficulty from config
        difficulty_str = self.load_config('difficulty')
        if difficulty_str:
            blockchain.difficulty = int(difficulty_str)
        
        return True

    def persist_all(self, blockchain: Blockchain) -> bool:
        success = True
        success &= self.save_chain(blockchain.chain)
        success &= self.save_pending_transactions(blockchain.pending_transactions)
        success &= self.save_nodes(blockchain.nodes)
        success &= self.save_config('difficulty', str(blockchain.difficulty))
        return success