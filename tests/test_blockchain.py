"""Tests for Blockchain core functionality."""
import pytest
import tempfile
import os
from blockchain.blockchain import Blockchain
from blockchain.block import Block
from blockchain.validation import validate_transaction, validate_chain


class TestBlockchain:
    def setup_method(self):
        self.blockchain = Blockchain(difficulty=2)

    def test_genesis_block_creation(self):
        assert len(self.blockchain.chain) == 0
        genesis = self.blockchain.create_genesis_block()
        assert len(self.blockchain.chain) == 1
        assert genesis.index == 0
        assert genesis.previous_hash == "0"
        assert genesis.proof == 1

    def test_new_transaction_valid(self):
        self.blockchain.create_genesis_block()
        tx = self.blockchain.new_transaction('ACC001', 100.0, 'deposit')
        assert tx['from_account'] == 'ACC001'
        assert tx['amount'] == 100.0
        assert tx['type'] == 'deposit'
        assert tx['to_account'] is None
        assert 'transaction_id' in tx
        assert len(self.blockchain.pending_transactions) == 1

    def test_new_transaction_transfer(self):
        self.blockchain.create_genesis_block()
        tx = self.blockchain.new_transaction('ACC001', 50.0, 'transfer', 'ACC002')
        assert tx['to_account'] == 'ACC002'
        assert len(self.blockchain.pending_transactions) == 1

    def test_new_transaction_invalid_amount(self):
        self.blockchain.create_genesis_block()
        with pytest.raises(ValueError):
            self.blockchain.new_transaction('ACC001', -100.0, 'deposit')

    def test_new_transaction_invalid_type(self):
        self.blockchain.create_genesis_block()
        with pytest.raises(ValueError):
            self.blockchain.new_transaction('ACC001', 100.0, 'invalid_type')

    def test_new_transaction_transfer_without_to_account(self):
        self.blockchain.create_genesis_block()
        with pytest.raises(ValueError):
            self.blockchain.new_transaction('ACC001', 100.0, 'transfer')

    def test_new_block(self):
        self.blockchain.create_genesis_block()
        self.blockchain.new_transaction('ACC001', 100.0, 'deposit')
        last_proof = self.blockchain.last_block().proof
        proof, timestamp = self.blockchain.proof_of_work(last_proof)
        block = self.blockchain.new_block(proof, timestamp)
        assert block.index == 1
        assert len(block.transactions) == 1
        assert block.proof == proof
        assert block.previous_hash == self.blockchain.chain[0].hash
        assert len(self.blockchain.pending_transactions) == 0

    def test_last_block(self):
        assert self.blockchain.last_block() is None
        self.blockchain.create_genesis_block()
        assert self.blockchain.last_block().index == 0

    def test_proof_of_work(self):
        self.blockchain.create_genesis_block()
        self.blockchain.new_transaction('ACC001', 100, 'deposit')
        last_proof = self.blockchain.last_block().proof
        proof, timestamp = self.blockchain.proof_of_work(last_proof)
        assert self.blockchain.valid_proof(last_proof, proof, timestamp=timestamp)

    def test_valid_proof(self):
        assert self.blockchain.valid_proof(1, 1) is False
        proof, timestamp = self.blockchain.proof_of_work(1)
        assert self.blockchain.valid_proof(1, proof, timestamp=timestamp) is True

    def test_valid_chain_valid(self):
        self.blockchain.create_genesis_block()
        self.blockchain.new_transaction('ACC001', 100.0, 'deposit')
        proof, timestamp = self.blockchain.proof_of_work(self.blockchain.last_block().proof)
        self.blockchain.new_block(proof, timestamp)
        assert self.blockchain.valid_chain(self.blockchain.chain) is True

    def test_valid_chain_invalid_hash(self):
        self.blockchain.create_genesis_block()
        self.blockchain.chain[0].hash = "invalid"
        assert self.blockchain.valid_chain(self.blockchain.chain) is False

    def test_get_block(self):
        self.blockchain.create_genesis_block()
        block = self.blockchain.get_block(0)
        assert block is not None
        assert block.index == 0
        assert self.blockchain.get_block(1) is None

    def test_register_node(self):
        result = self.blockchain.register_node('http://localhost:5001')
        assert result is True
        assert 'http://localhost:5001' in self.blockchain.nodes

    def test_register_node_invalid(self):
        result = self.blockchain.register_node('invalid_url')
        assert result is False


class TestTransactionValidation:
    def test_valid_deposit(self):
        tx = {'from_account': 'ACC001', 'amount': 100, 'type': 'deposit'}
        valid, error = validate_transaction(tx)
        assert valid is True
        assert error is None

    def test_valid_withdrawal(self):
        tx = {'from_account': 'ACC001', 'amount': 50, 'type': 'withdrawal'}
        valid, error = validate_transaction(tx)
        assert valid is True

    def test_valid_transfer(self):
        tx = {'from_account': 'ACC001', 'to_account': 'ACC002', 'amount': 25, 'type': 'transfer'}
        valid, error = validate_transaction(tx)
        assert valid is True

    def test_invalid_missing_field(self):
        tx = {'from_account': 'ACC001', 'type': 'deposit'}
        valid, error = validate_transaction(tx)
        assert valid is False
        assert 'amount' in error

    def test_invalid_amount(self):
        tx = {'from_account': 'ACC001', 'amount': -10, 'type': 'deposit'}
        valid, error = validate_transaction(tx)
        assert valid is False

    def test_invalid_type(self):
        tx = {'from_account': 'ACC001', 'amount': 100, 'type': 'invalid'}
        valid, error = validate_transaction(tx)
        assert valid is False

    def test_transfer_without_to_account(self):
        tx = {'from_account': 'ACC001', 'amount': 100, 'type': 'transfer'}
        valid, error = validate_transaction(tx)
        assert valid is False
        assert 'destination' in error.lower()


class TestChainValidation:
    def test_valid_chain(self):
        blockchain = Blockchain(difficulty=2)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = blockchain.proof_of_work(blockchain.last_block().proof)
        blockchain.new_block(proof, timestamp)
        is_valid, issues = validate_chain(blockchain.chain, 2)
        assert is_valid is True
        assert len(issues) == 0

    def test_empty_chain(self):
        is_valid, issues = validate_chain([], 2)
        assert is_valid is False
        assert 'empty' in issues[0].lower()

    def test_genesis_wrong_index(self):
        blockchain = Blockchain(difficulty=2)
        blockchain.create_genesis_block()
        blockchain.chain[0].index = 1
        is_valid, issues = validate_chain(blockchain.chain, 2)
        assert is_valid is False