"""Tests for Block model."""
import pytest
from blockchain.block import Block


class TestBlock:
    def test_block_creation(self):
        block = Block(
            index=1,
            timestamp=1234567890.0,
            transactions=[{'from': 'A', 'to': 'B', 'amount': 100}],
            proof=12345,
            previous_hash='abc123'
        )
        assert block.index == 1
        assert block.timestamp == 1234567890.0
        assert len(block.transactions) == 1
        assert block.proof == 12345
        assert block.previous_hash == 'abc123'
        assert block.hash is not None
        assert len(block.hash) == 64

    def test_block_hash_deterministic(self):
        block1 = Block(1, 1234567890.0, [{'amount': 100}], 12345, 'abc123')
        block2 = Block(1, 1234567890.0, [{'amount': 100}], 12345, 'abc123')
        assert block1.hash == block2.hash

    def test_block_hash_changes_with_data(self):
        block1 = Block(1, 1234567890.0, [{'amount': 100}], 12345, 'abc123')
        block2 = Block(1, 1234567890.0, [{'amount': 200}], 12345, 'abc123')
        assert block1.hash != block2.hash

    def test_block_to_dict(self):
        block = Block(1, 1234567890.0, [{'amount': 100}], 12345, 'abc123')
        data = block.to_dict()
        assert data['index'] == 1
        assert data['timestamp'] == 1234567890.0
        assert data['proof'] == 12345
        assert data['previous_hash'] == 'abc123'
        assert 'hash' in data

    def test_block_from_dict(self):
        original = Block(1, 1234567890.0, [{'amount': 100}], 12345, 'abc123')
        data = original.to_dict()
        restored = Block.from_dict(data)
        assert restored.index == original.index
        assert restored.timestamp == original.timestamp
        assert restored.proof == original.proof
        assert restored.previous_hash == original.previous_hash
        assert restored.hash == original.hash
        assert restored.transactions == original.transactions

    def test_block_equality(self):
        block1 = Block(1, 1234567890.0, [{'amount': 100}], 12345, 'abc123')
        block2 = Block(1, 1234567890.0, [{'amount': 100}], 12345, 'abc123')
        block3 = Block(2, 1234567890.0, [{'amount': 100}], 12345, 'abc123')
        assert block1 == block2
        assert block1 != block3

    def test_compute_hash(self):
        block = Block(1, 1234567890.0, [{'amount': 100}], 12345, 'abc123')
        computed = block.compute_hash()
        assert computed == block.hash
        assert len(computed) == 64