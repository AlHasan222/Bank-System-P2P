"""P2P Node implementation."""
import logging
import threading
import time
from typing import Optional, Set
from blockchain.blockchain import Blockchain
from blockchain.storage import BlockchainStorage
from blockchain.consensus import ConsensusManager
from blockchain.config import Config


logger = logging.getLogger(__name__)


class Node:
    def __init__(self, host: str = Config.DEFAULT_HOST, port: int = Config.DEFAULT_PORT):
        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        
        self.blockchain = Blockchain()
        self.storage = BlockchainStorage()
        self.consensus = ConsensusManager(self.blockchain)
        
        self._sync_thread: Optional[threading.Thread] = None
        self._running = False
        self._sync_interval = Config.SYNC_INTERVAL

    def start(self):
        self.storage.initialize_blockchain(self.blockchain)
        self._running = True
        self._start_sync_loop()
        logger.info(f"Node started at {self.url}")

    def stop(self):
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5)
        self.storage.persist_all(self.blockchain)
        logger.info(f"Node stopped at {self.url}")

    def _start_sync_loop(self):
        def sync_loop():
            while self._running:
                time.sleep(self._sync_interval)
                if self._running:
                    try:
                        self.consensus.sync_chain()
                    except Exception as e:
                        logger.error(f"Sync loop error: {e}")
        
        self._sync_thread = threading.Thread(target=sync_loop, daemon=True)
        self._sync_thread.start()

    def register_peer(self, peer_url: str) -> bool:
        from blockchain.utils import parse_node_url
        parsed = parse_node_url(peer_url)
        if not parsed:
            return False
        
        if parsed == self.url:
            logger.warning("Cannot register self as peer")
            return False
        
        success = self.blockchain.register_node(parsed)
        if success:
            self.storage.save_nodes(self.blockchain.nodes)
            self.consensus.sync_chain()
        return success

    def mine_block(self) -> Optional[dict]:
        if not self.blockchain.pending_transactions:
            logger.warning("No pending transactions to mine")
            return None
        
        last_block = self.blockchain.last_block()
        if not last_block:
            logger.error("No genesis block found")
            return None
        
        proof, timestamp = self.blockchain.proof_of_work(
            last_block.proof,
            self.blockchain.pending_transactions,
            last_block.hash
        )
        block = self.blockchain.new_block(proof, timestamp)
        
        self.storage.save_chain(self.blockchain.chain)
        self.storage.save_pending_transactions(self.blockchain.pending_transactions)
        
        self.consensus.announce_new_block(block)
        
        return block.to_dict()

    def add_transaction(self, from_account: str, amount: float, tx_type: str, to_account: Optional[str] = None) -> dict:
        tx = self.blockchain.new_transaction(from_account, amount, tx_type, to_account)
        self.storage.save_pending_transactions(self.blockchain.pending_transactions)
        return tx

    def get_chain(self) -> list:
        return [block.to_dict() for block in self.blockchain.chain]

    def get_pending_transactions(self) -> list:
        return self.blockchain.pending_transactions.copy()

    def get_nodes(self) -> list:
        return list(self.blockchain.nodes)

    def resolve_conflicts(self) -> bool:
        return self.consensus.sync_chain()

    def validate_chain(self) -> dict:
        from blockchain.validation import validate_chain
        is_valid, issues = validate_chain(self.blockchain.chain, self.blockchain.difficulty)
        return {
            'valid': is_valid,
            'block_count': len(self.blockchain.chain),
            'issues': issues
        }

    def get_info(self) -> dict:
        return self.blockchain.get_chain_info()