"""Tests for REST API endpoints."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from blockchain.node import Node
from blockchain.blockchain import Blockchain
from blockchain.block import Block
from api.app import create_app


class TestAPI:
    def setup_method(self):
        self.blockchain = Blockchain(difficulty=2)
        self.blockchain.create_genesis_block()
        self.node = Node.__new__(Node)
        self.node.blockchain = self.blockchain
        self.node.url = 'http://localhost:5000'
        self.node.storage = Mock()
        self.node.consensus = Mock()
        
        self.app = create_app(self.node)
        self.client = self.app.test_client()

    def test_health_endpoint(self):
        response = self.client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['status'] == 'healthy'

    def test_get_chain(self):
        self.blockchain.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = self.blockchain.proof_of_work(self.blockchain.last_block().proof)
        self.blockchain.new_block(proof, timestamp)
        
        response = self.client.get('/chain')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['length'] == 2
        assert len(data['chain']) == 2

    def test_get_block_by_index(self):
        response = self.client.get('/chain/0')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['block']['index'] == 0

    def test_get_block_not_found(self):
        response = self.client.get('/chain/999')
        assert response.status_code == 404

    def test_validate_chain(self):
        response = self.client.get('/validate')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['valid'] is True
        assert data['block_count'] == 1

    def test_new_transaction_deposit(self):
        response = self.client.post('/transactions/new', 
            data=json.dumps({'from_account': 'ACC001', 'amount': 100, 'type': 'deposit'}),
            content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['transaction']['type'] == 'deposit'

    def test_new_transaction_transfer(self):
        response = self.client.post('/transactions/new',
            data=json.dumps({'from_account': 'ACC001', 'to_account': 'ACC002', 'amount': 50, 'type': 'transfer'}),
            content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['transaction']['to_account'] == 'ACC002'

    def test_new_transaction_invalid(self):
        response = self.client.post('/transactions/new',
            data=json.dumps({'from_account': 'ACC001', 'amount': -100, 'type': 'deposit'}),
            content_type='application/json')
        assert response.status_code == 400

    def test_get_pending_transactions(self):
        self.blockchain.pending_transactions = [
            {'transaction_id': 'tx1', 'from_account': 'ACC001', 'amount': 100, 'type': 'deposit'}
        ]
        response = self.client.get('/transactions/pending')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 1

    def test_mine_block(self):
        self.blockchain.new_transaction('ACC001', 100, 'deposit')
        self.node.consensus.announce_new_block = Mock(return_value=0)
        
        response = self.client.get('/mine')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'block' in data

    def test_mine_no_pending(self):
        self.blockchain.pending_transactions = []
        response = self.client.get('/mine')
        assert response.status_code == 409

    def test_register_nodes(self):
        self.node.register_peer = Mock(return_value=True)
        self.node.storage.save_nodes = Mock(return_value=True)
        self.node.consensus.sync_chain = Mock(return_value=False)
        
        response = self.client.post('/nodes/register',
            data=json.dumps({'nodes': ['http://localhost:5001', 'http://localhost:5002']}),
            content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['registered']) == 2

    def test_register_nodes_invalid(self):
        response = self.client.post('/nodes/register',
            data=json.dumps({'nodes': []}),
            content_type='application/json')
        assert response.status_code == 400

    def test_get_nodes(self):
        self.blockchain.nodes = {'http://localhost:5001', 'http://localhost:5002'}
        response = self.client.get('/nodes')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 2

    def test_resolve_conflicts(self):
        self.node.resolve_conflicts = Mock(return_value=True)
        response = self.client.get('/nodes/resolve')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['replaced'] is True

    def test_receive_block(self):
        # Use fresh blockchain - setup_method already created genesis
        # Clear any pending transactions first
        self.blockchain.pending_transactions = []
        self.blockchain.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = self.blockchain.proof_of_work(self.blockchain.last_block().proof)
        # Create block but don't add to chain yet
        from blockchain.block import Block
        block = Block(
            index=1,
            timestamp=timestamp,
            transactions=self.blockchain.pending_transactions.copy(),
            proof=proof,
            previous_hash=self.blockchain.last_block().hash
        )
        
        self.node.storage.save_chain = Mock(return_value=True)
        
        response = self.client.post('/blocks/new',
            data=json.dumps(block.to_dict()),
            content_type='application/json')
        assert response.status_code == 201

    def test_info_endpoint(self):
        response = self.client.get('/info')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'length' in data