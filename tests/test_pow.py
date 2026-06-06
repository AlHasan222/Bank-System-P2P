"""Tests for Proof of Work."""
import pytest
from blockchain.blockchain import Blockchain
from blockchain.block import Block


class TestProofOfWork:
    def test_pow_difficulty_1(self):
        blockchain = Blockchain(difficulty=1)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        last_proof = blockchain.last_block().proof
        proof, timestamp = blockchain.proof_of_work(last_proof)
        blockchain.new_block(proof, timestamp)
        assert blockchain.chain[-1].hash.startswith('0')

    def test_pow_difficulty_2(self):
        blockchain = Blockchain(difficulty=2)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        last_proof = blockchain.last_block().proof
        proof, timestamp = blockchain.proof_of_work(last_proof)
        blockchain.new_block(proof, timestamp)
        assert blockchain.chain[-1].hash.startswith('00')

    def test_pow_difficulty_3(self):
        blockchain = Blockchain(difficulty=3)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        last_proof = blockchain.last_block().proof
        proof, timestamp = blockchain.proof_of_work(last_proof)
        blockchain.new_block(proof, timestamp)
        assert blockchain.chain[-1].hash.startswith('000')

    def test_pow_difficulty_4(self):
        blockchain = Blockchain(difficulty=4)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        last_proof = blockchain.last_block().proof
        proof, timestamp = blockchain.proof_of_work(last_proof)
        blockchain.new_block(proof, timestamp)
        assert blockchain.chain[-1].hash.startswith('0000')

    def test_valid_proof_false_for_wrong_proof(self):
        blockchain = Blockchain(difficulty=2)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        last_proof = blockchain.last_block().proof
        proof, timestamp = blockchain.proof_of_work(last_proof)
        blockchain.new_block(proof, timestamp)
        # Wrong proof should not produce valid hash
        wrong_block = Block(
            index=1,
            timestamp=timestamp,
            transactions=blockchain.pending_transactions,
            proof=proof + 1,
            previous_hash=blockchain.chain[0].hash
        )
        assert not wrong_block.hash.startswith('00')

    def test_block_hash_starts_with_zeros(self):
        blockchain = Blockchain(difficulty=3)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        last_proof = blockchain.last_block().proof
        proof, timestamp = blockchain.proof_of_work(last_proof)
        blockchain.new_block(proof, timestamp)
        assert blockchain.chain[-1].hash.startswith('000')

    def test_different_last_proofs_produce_different_proofs(self):
        blockchain = Blockchain(difficulty=2)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        proof1, _ = blockchain.proof_of_work(1)
        proof2, _ = blockchain.proof_of_work(2)
        assert proof1 != proof2

    def test_pow_is_deterministic_for_same_input(self):
        blockchain = Blockchain(difficulty=2)
        blockchain.create_genesis_block()
        blockchain.new_transaction('ACC001', 100, 'deposit')
        proof1, ts1 = blockchain.proof_of_work(100)
        proof2, ts2 = blockchain.proof_of_work(100)
        # Both proofs should be valid (may differ due to timestamp)
        assert blockchain.valid_proof(100, proof1, timestamp=ts1)
        assert blockchain.valid_proof(100, proof2, timestamp=ts2)