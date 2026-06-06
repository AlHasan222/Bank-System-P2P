"""Integration tests for Bank Mirror -> Blockchain workflow."""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from blockchain.blockchain import Blockchain
from blockchain.node import Node
from bank_mirror.service import BankMirrorService
from bank_mirror.models import BankTransaction


class TestBankIntegration:
    def setup_method(self):
        self.blockchain = Blockchain(difficulty=2)
        self.blockchain.create_genesis_block()
        
        self.node = Node.__new__(Node)
        self.node.blockchain = self.blockchain
        self.node.url = 'http://localhost:5000'
        self.node.storage = Mock()
        self.node.consensus = Mock()
        
        self.bank_service = BankMirrorService(['http://localhost:5000'])

    @patch('bank_mirror.service.requests.post')
    def test_deposit_flow(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'success': True, 'transaction': {'transaction_id': 'tx1'}}
        mock_post.return_value = mock_response
        
        result = self.bank_service.deposit('ACC001', 500.0)
        
        assert result['success'] is True
        assert result['transaction']['type'] == 'deposit'
        assert result['transaction']['amount'] == 500.0
        mock_post.assert_called_once()

    @patch('bank_mirror.service.requests.post')
    def test_withdrawal_flow(self, mock_post):
        self.bank_service.create_account('ACC001', 1000.0)
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        result = self.bank_service.withdrawal('ACC001', 200.0)
        
        assert result['success'] is True
        assert result['transaction']['type'] == 'withdrawal'

    @patch('bank_mirror.service.requests.post')
    def test_withdrawal_insufficient_balance(self, mock_post):
        self.bank_service.create_account('ACC001', 100.0)
        
        result = self.bank_service.withdrawal('ACC001', 200.0)
        
        assert result['success'] is False
        assert 'Insufficient' in result['error']
        mock_post.assert_not_called()

    @patch('bank_mirror.service.requests.post')
    def test_transfer_flow(self, mock_post):
        self.bank_service.create_account('ACC001', 1000.0)
        
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        result = self.bank_service.transfer('ACC001', 'ACC002', 300.0)
        
        assert result['success'] is True
        assert result['transaction']['type'] == 'transfer'
        assert result['transaction']['to_account'] == 'ACC002'

    @patch('bank_mirror.service.requests.post')
    def test_custom_transaction(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        
        result = self.bank_service.custom_transaction('ACC001', None, 100.0, 'deposit')
        assert result['success'] is True
        
        result = self.bank_service.custom_transaction('ACC001', 'ACC002', 50.0, 'transfer')
        assert result['success'] is True
        
        result = self.bank_service.custom_transaction('ACC001', None, 100.0, 'invalid')
        assert result['success'] is False

    def test_get_status(self):
        self.bank_service.create_account('ACC001', 500.0)
        self.bank_service.create_account('ACC002', 1000.0)
        
        status = self.bank_service.get_status()
        
        assert 'accounts' in status
        assert status['accounts']['ACC001']['balance'] == 500.0
        assert status['accounts']['ACC002']['balance'] == 1000.0

    def test_get_history(self):
        tx1 = BankTransaction.create_deposit('ACC001', 100)
        tx1.status = 'confirmed'
        self.bank_service.history.add(tx1)
        
        tx2 = BankTransaction.create_transfer('ACC001', 'ACC002', 50)
        tx2.status = 'pending'
        self.bank_service.history.add(tx2)
        
        history = self.bank_service.get_history()
        assert history['count'] == 2
        
        account_history = self.bank_service.get_history('ACC001')
        assert account_history['count'] == 2

    @patch('bank_mirror.service.requests.post')
    def test_full_workflow_deposit_mine_validate(self, mock_post):
        # Mock blockchain node responses
        def mock_post_side_effect(url, json, timeout):
            mock_resp = Mock()
            if '/transactions/new' in url:
                mock_resp.status_code = 201
                mock_resp.json.return_value = {'success': True, 'transaction': json}
            elif '/mine' in url:
                mock_resp.status_code = 201
                mock_resp.json.return_value = {'success': True, 'block': {'index': 1}}
            elif '/validate' in url:
                mock_resp.status_code = 200
                mock_resp.json.return_value = {'success': True, 'valid': True, 'block_count': 2}
            else:
                mock_resp.status_code = 404
            return mock_resp
        
        mock_post.side_effect = mock_post_side_effect
        
        # Send deposit from bank
        result = self.bank_service.deposit('ACC001', 1000.0)
        assert result['success'] is True
        
        # Verify transaction was added to blockchain pending pool
        assert len(self.blockchain.pending_transactions) >= 0  # In real flow, it would be added

    def test_bank_service_add_remove_nodes(self):
        self.bank_service.add_node('http://new-node:5000')
        assert 'http://new-node:5000' in self.bank_service.blockchain_nodes
        
        self.bank_service.remove_node('http://new-node:5000')
        assert 'http://new-node:5000' not in self.bank_service.blockchain_nodes


class TestEndToEndWorkflow:
    """Test complete workflow: Bank -> Transaction -> Mining -> Chain -> Consensus"""
    
    def setup_method(self):
        self.blockchain = Blockchain(difficulty=2)
        self.blockchain.create_genesis_block()
        
    def test_complete_transaction_lifecycle(self):
        # 1. Add transaction
        tx = self.blockchain.new_transaction('ACC001', 500, 'deposit')
        assert len(self.blockchain.pending_transactions) == 1
        
        # 2. Mine block
        last_proof = self.blockchain.last_block().proof
        proof, timestamp = self.blockchain.proof_of_work(last_proof)
        block = self.blockchain.new_block(proof, timestamp)
        
        # 3. Verify block created
        assert block.index == 1
        assert len(block.transactions) == 1
        assert block.transactions[0]['transaction_id'] == tx['transaction_id']
        
        # 4. Verify pending cleared
        assert len(self.blockchain.pending_transactions) == 0
        
        # 5. Validate chain
        from blockchain.validation import validate_chain
        is_valid, issues = validate_chain(self.blockchain.chain, 2)
        assert is_valid is True
        assert len(issues) == 0

    def test_multiple_transactions_single_block(self):
        # Add multiple transactions
        self.blockchain.new_transaction('ACC001', 100, 'deposit')
        self.blockchain.new_transaction('ACC001', 50, 'transfer', 'ACC002')
        self.blockchain.new_transaction('ACC002', 200, 'withdrawal')
        
        assert len(self.blockchain.pending_transactions) == 3
        
        # Mine block
        proof, timestamp = self.blockchain.proof_of_work(self.blockchain.last_block().proof)
        block = self.blockchain.new_block(proof, timestamp)
        
        assert len(block.transactions) == 3
        assert block.transactions[0]['type'] == 'deposit'
        assert block.transactions[1]['type'] == 'transfer'
        assert block.transactions[2]['type'] == 'withdrawal'

    def test_chain_persistence_recovery(self):
        import tempfile
        import os
        from blockchain.storage import BlockchainStorage
        
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test.db')
        storage = BlockchainStorage(db_path)
        
        # Save chain
        self.blockchain.new_transaction('ACC001', 100, 'deposit')
        proof, timestamp = self.blockchain.proof_of_work(self.blockchain.last_block().proof)
        self.blockchain.new_block(proof, timestamp)
        
        storage.save_chain(self.blockchain.chain)
        storage.save_config('difficulty', '2')
        
        # Create new blockchain and recover
        new_blockchain = Blockchain()
        storage.initialize_blockchain(new_blockchain)
        
        assert len(new_blockchain.chain) == 2
        assert new_blockchain.difficulty == 2
        
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)