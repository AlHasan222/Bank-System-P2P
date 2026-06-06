"""Tests for SQLite persistence."""
import pytest
import tempfile
import os
from blockchain.storage import BlockchainStorage
from blockchain.blockchain import Blockchain
from blockchain.block import Block


class TestStorage:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_blockchain.db')
        self.storage = BlockchainStorage(self.db_path)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_init_db_creates_tables(self):
        self.storage._init_db()
        # Tables should exist
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            assert 'blocks' in tables
            assert 'pending_transactions' in tables
            assert 'nodes' in tables
            assert 'config' in tables

    def test_save_and_load_chain(self):
        blockchain = Blockchain(difficulty=2)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = blockchain.proof_of_work(blockchain.last_block().proof)
        blockchain.new_block(proof, timestamp)
        
        assert self.storage.save_chain(blockchain.chain)
        loaded = self.storage.load_chain()
        
        assert len(loaded) == 2
        assert loaded[0].index == 0
        assert loaded[1].index == 1
        assert loaded[0].hash == blockchain.chain[0].hash
        assert loaded[1].hash == blockchain.chain[1].hash

    def test_load_empty_chain(self):
        loaded = self.storage.load_chain()
        assert loaded == []

    def test_save_and_load_pending_transactions(self):
        transactions = [
            {'transaction_id': 'tx1', 'timestamp': 1234567890.0, 'from_account': 'ACC001', 'to_account': None, 'amount': 100, 'type': 'deposit'},
            {'transaction_id': 'tx2', 'timestamp': 1234567891.0, 'from_account': 'ACC001', 'to_account': 'ACC002', 'amount': 50, 'type': 'transfer'}
        ]
        
        assert self.storage.save_pending_transactions(transactions)
        loaded = self.storage.load_pending_transactions()
        
        assert len(loaded) == 2
        assert loaded[0]['transaction_id'] == 'tx1'
        assert loaded[1]['transaction_id'] == 'tx2'

    def test_load_empty_pending_transactions(self):
        loaded = self.storage.load_pending_transactions()
        assert loaded == []

    def test_save_and_load_nodes(self):
        nodes = {'http://localhost:5001', 'http://localhost:5002'}
        
        assert self.storage.save_nodes(nodes)
        loaded = self.storage.load_nodes()
        
        assert loaded == nodes

    def test_load_empty_nodes(self):
        loaded = self.storage.load_nodes()
        assert loaded == set()

    def test_save_and_load_config(self):
        assert self.storage.save_config('difficulty', '4')
        value = self.storage.load_config('difficulty')
        assert value == '4'
        
        default = self.storage.load_config('nonexistent', 'default_value')
        assert default == 'default_value'

    def test_initialize_blockchain_new(self):
        blockchain = Blockchain(difficulty=3)
        self.storage.initialize_blockchain(blockchain)
        
        assert len(blockchain.chain) == 1
        assert blockchain.chain[0].index == 0
        assert blockchain.difficulty == 3

    def test_initialize_blockchain_existing(self):
        # First, create and save a blockchain
        blockchain1 = Blockchain(difficulty=2)
        blockchain1.create_genesis_block()
        blockchain1.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = blockchain1.proof_of_work(blockchain1.last_block().proof)
        blockchain1.new_block(proof, timestamp)
        self.storage.save_chain(blockchain1.chain)
        self.storage.save_config('difficulty', '2')
        
        # Now initialize a new blockchain instance
        blockchain2 = Blockchain()
        self.storage.initialize_blockchain(blockchain2)
        
        assert len(blockchain2.chain) == 2
        assert blockchain2.difficulty == 2

    def test_persist_all(self):
        blockchain = Blockchain(difficulty=2)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = blockchain.proof_of_work(blockchain.last_block().proof)
        blockchain.new_block(proof, timestamp)
        blockchain.register_node('http://localhost:5001')
        
        assert self.storage.persist_all(blockchain)
        
        # Verify all data persisted
        loaded_chain = self.storage.load_chain()
        loaded_pending = self.storage.load_pending_transactions()
        loaded_nodes = self.storage.load_nodes()
        
        assert len(loaded_chain) == 2
        assert len(loaded_pending) == 0  # Cleared after mining
        assert 'http://localhost:5001' in loaded_nodes

    def test_corrupted_database_handling(self):
        # Write invalid data to db
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO blocks (block_index, timestamp, transactions, proof, previous_hash, hash) VALUES (999, 0, '[]', 1, 'invalid', 'hash')")
            conn.commit()
        
        # Should not crash, return empty or skip invalid rows
        loaded = self.storage.load_chain()
        # Should handle gracefully (may return partial or empty)
        assert isinstance(loaded, list)