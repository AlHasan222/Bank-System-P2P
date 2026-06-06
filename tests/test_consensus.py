"""Tests for consensus mechanism."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from blockchain.blockchain import Blockchain
from blockchain.block import Block
from blockchain.consensus import ConsensusManager


class TestConsensus:
    def setup_method(self):
        self.blockchain = Blockchain(difficulty=2)
        self.blockchain.create_genesis_block()
        self.consensus = ConsensusManager(self.blockchain)

    def test_sync_chain_no_nodes(self):
        result = self.consensus.sync_chain()
        assert result is False

    def test_resolve_conflicts_no_nodes(self):
        result = self.blockchain.resolve_conflicts()
        assert result is False

    @patch('blockchain.consensus.requests.get')
    def test_resolve_conflicts_longer_valid_chain(self, mock_get):
        longer_chain = Blockchain(difficulty=2)
        longer_chain.create_genesis_block()
        longer_chain.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = longer_chain.proof_of_work(longer_chain.last_block().proof)
        longer_chain.new_block(proof, timestamp)
        longer_chain.new_transaction('ACC002', 200, 'deposit')
        proof, timestamp = longer_chain.proof_of_work(longer_chain.last_block().proof)
        longer_chain.new_block(proof, timestamp)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'chain': [b.to_dict() for b in longer_chain.chain],
            'length': len(longer_chain.chain)
        }
        mock_get.return_value = mock_response
        
        self.blockchain.nodes.add('http://peer1:5000')
        result = self.blockchain.resolve_conflicts()
        assert result is True
        assert len(self.blockchain.chain) == len(longer_chain.chain)

    @patch('blockchain.consensus.requests.get')
    def test_resolve_conflicts_invalid_chain_rejected(self, mock_get):
        invalid_chain = Blockchain(difficulty=2)
        invalid_chain.create_genesis_block()
        invalid_chain.chain[0].hash = "tampered"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'chain': [b.to_dict() for b in invalid_chain.chain],
            'length': len(invalid_chain.chain)
        }
        mock_get.return_value = mock_response
        
        self.blockchain.nodes.add('http://peer1:5000')
        result = self.blockchain.resolve_conflicts()
        assert result is False
        assert len(self.blockchain.chain) == 1

    @patch('blockchain.consensus.requests.get')
    def test_resolve_conflicts_shorter_chain_ignored(self, mock_get):
        shorter_chain = Blockchain(difficulty=2)
        shorter_chain.create_genesis_block()
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'chain': [b.to_dict() for b in shorter_chain.chain],
            'length': len(shorter_chain.chain)
        }
        mock_get.return_value = mock_response
        
        self.blockchain.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = self.blockchain.proof_of_work(self.blockchain.last_block().proof)
        self.blockchain.new_block(proof, timestamp)
        
        self.blockchain.nodes.add('http://peer1:5000')
        result = self.blockchain.resolve_conflicts()
        assert result is False

    @patch('blockchain.consensus.requests.get')
    def test_fetch_peer_chains(self, mock_get):
        peer_chain = Blockchain(difficulty=2)
        peer_chain.create_genesis_block()
        peer_chain.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = peer_chain.proof_of_work(peer_chain.last_block().proof)
        peer_chain.new_block(proof, timestamp)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'chain': [b.to_dict() for b in peer_chain.chain],
            'length': len(peer_chain.chain)
        }
        mock_get.return_value = mock_response
        
        self.blockchain.nodes.add('http://peer1:5000')
        chains = self.consensus.fetch_peer_chains()
        assert len(chains) == 1
        assert chains[0][2] == 2

    @patch('blockchain.consensus.requests.post')
    def test_announce_new_block(self, mock_post):
        self.blockchain.create_genesis_block()
        self.blockchain.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = self.blockchain.proof_of_work(self.blockchain.last_block().proof)
        block = self.blockchain.new_block(proof, timestamp)
        
        self.blockchain.nodes.add('http://peer1:5000')
        self.blockchain.nodes.add('http://peer2:5000')
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        announced = self.consensus.announce_new_block(block)
        assert announced == 2
        assert mock_post.call_count == 2

    def test_validate_and_compare_chains(self):
        longer = Blockchain(difficulty=2)
        longer.create_genesis_block()
        longer.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = longer.proof_of_work(longer.last_block().proof)
        longer.new_block(proof, timestamp)
        
        invalid = Blockchain(difficulty=2)
        invalid.create_genesis_block()
        invalid.chain[0].hash = "tampered"
        
        chains = [
            ('peer1', longer.chain, len(longer.chain)),
            ('peer2', invalid.chain, len(invalid.chain))
        ]
        
        result = self.consensus.validate_and_compare_chains(chains)
        assert result is not None
        assert len(result) == 2