"""API routes for the blockchain node."""
import logging
from flask import Blueprint, request, jsonify
from api.schemas import TransactionRequest, NodeRegistrationRequest, BlockRequest
from api.errors import ValidationError, NotFoundError, ConflictError, InternalError
from blockchain.node import Node

logger = logging.getLogger(__name__)

bp = Blueprint('api', __name__)

node: Node = None


def init_routes(blockchain_node: Node):
    global node
    node = blockchain_node





@bp.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'status': 'healthy', 'node': node.url})


@bp.route('/chain', methods=['GET'])
def get_chain():
    chain = node.get_chain()
    return jsonify({
        'success': True,
        'chain': chain,
        'length': len(chain)
    })


@bp.route('/chain/<int:index>', methods=['GET'])
def get_block(index):
    block = node.blockchain.get_block(index)
    if not block:
        raise NotFoundError(f"Block at index {index} not found")
    return jsonify({'success': True, 'block': block.to_dict()})


@bp.route('/validate', methods=['GET'])
def validate_chain():
    result = node.validate_chain()
    return jsonify({'success': True, **result})


@bp.route('/transactions/new', methods=['POST'])
def new_transaction():
    data = request.get_json()
    if not data:
        raise ValidationError("Request body must be JSON")
    
    tx_request = TransactionRequest.from_dict(data)
    is_valid, error = tx_request.validate()
    if not is_valid:
        raise ValidationError(error)
    
    try:
        tx = node.add_transaction(
            tx_request.from_account,
            tx_request.amount,
            tx_request.type,
            tx_request.to_account
        )
        return jsonify({'success': True, 'transaction': tx}), 201
    except ValueError as e:
        raise ValidationError(str(e))


@bp.route('/transactions/pending', methods=['GET'])
def get_pending_transactions():
    pending = node.get_pending_transactions()
    return jsonify({'success': True, 'transactions': pending, 'count': len(pending)})


@bp.route('/mine', methods=['GET'])
def mine():
    block = node.mine_block()
    if not block:
        raise ConflictError("No pending transactions to mine")
    return jsonify({'success': True, 'block': block}), 201


@bp.route('/nodes/register', methods=['POST'])
def register_nodes():
    data = request.get_json()
    if not data:
        raise ValidationError("Request body must be JSON")
    
    reg_request = NodeRegistrationRequest.from_dict(data)
    if not reg_request.nodes:
        raise ValidationError("nodes list is required")
    
    registered = []
    for peer_url in reg_request.nodes:
        if node.register_peer(peer_url):
            registered.append(peer_url)
    
    return jsonify({
        'success': True,
        'message': f'Registered {len(registered)} nodes',
        'registered': registered,
        'total_nodes': list(node.blockchain.nodes)
    }), 201


@bp.route('/nodes', methods=['GET'])
def get_nodes():
    return jsonify({
        'success': True,
        'nodes': list(node.blockchain.nodes),
        'count': len(node.blockchain.nodes)
    })


@bp.route('/nodes/resolve', methods=['GET'])
def resolve_conflicts():
    replaced = node.resolve_conflicts()
    return jsonify({
        'success': True,
        'replaced': replaced,
        'message': 'Chain was replaced' if replaced else 'Chain is authoritative',
        'chain': node.get_chain()
    })


@bp.route('/blocks/new', methods=['POST'])
def receive_block():
    data = request.get_json()
    if not data:
        raise ValidationError("Request body must be JSON")
    
    try:
        block_request = BlockRequest.from_dict(data)
        from blockchain.block import Block
        block = Block.from_dict(block_request.__dict__)
        
        from blockchain.validation import validate_block
        is_valid, error = validate_block(block, node.blockchain.last_block(), node.blockchain.difficulty)
        if not is_valid:
            raise ValidationError(f"Invalid block: {error}")
        
        node.blockchain.chain.append(block)
        node.storage.save_chain(node.blockchain.chain)
        
        return jsonify({'success': True, 'message': 'Block added'}), 201
    except Exception as e:
        raise InternalError(f"Failed to process block: {e}")


@bp.route('/info', methods=['GET'])
def get_info():
    return jsonify({'success': True, **node.get_info()})