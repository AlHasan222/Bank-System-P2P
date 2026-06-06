"""Bank Mirror Flask server."""
import logging
from flask import Flask, request, jsonify
from bank_mirror.service import BankMirrorService


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

bank_service: BankMirrorService = None


def create_app(blockchain_nodes: list = None) -> Flask:
    global bank_service
    bank_service = BankMirrorService(blockchain_nodes or [])
    return app


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'success': True, 'status': 'healthy', 'service': 'bank-mirror'})


@app.route('/send/deposit', methods=['POST'])
def send_deposit():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body must be JSON'}), 400
    
    from_account = data.get('from_account')
    amount = data.get('amount')
    
    if not from_account or amount is None:
        return jsonify({'success': False, 'error': 'from_account and amount are required'}), 400
    
    result = bank_service.deposit(from_account, float(amount))
    status = 200 if result['success'] else 400
    return jsonify(result), status


@app.route('/send/withdrawal', methods=['POST'])
def send_withdrawal():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body must be JSON'}), 400
    
    from_account = data.get('from_account')
    amount = data.get('amount')
    
    if not from_account or amount is None:
        return jsonify({'success': False, 'error': 'from_account and amount are required'}), 400
    
    result = bank_service.withdrawal(from_account, float(amount))
    status = 200 if result['success'] else 400
    return jsonify(result), status


@app.route('/send/transfer', methods=['POST'])
def send_transfer():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body must be JSON'}), 400
    
    from_account = data.get('from_account')
    to_account = data.get('to_account')
    amount = data.get('amount')
    
    if not from_account or not to_account or amount is None:
        return jsonify({'success': False, 'error': 'from_account, to_account, and amount are required'}), 400
    
    result = bank_service.transfer(from_account, to_account, float(amount))
    status = 200 if result['success'] else 400
    return jsonify(result), status


@app.route('/send/custom', methods=['POST'])
def send_custom():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request body must be JSON'}), 400
    
    from_account = data.get('from_account')
    to_account = data.get('to_account')
    amount = data.get('amount')
    tx_type = data.get('type')
    
    if not from_account or amount is None or not tx_type:
        return jsonify({'success': False, 'error': 'from_account, amount, and type are required'}), 400
    
    result = bank_service.custom_transaction(from_account, to_account, float(amount), tx_type)
    status = 200 if result['success'] else 400
    return jsonify(result), status


@app.route('/status', methods=['GET'])
def get_status():
    return jsonify({'success': True, **bank_service.get_status()})


@app.route('/history', methods=['GET'])
def get_history():
    account_id = request.args.get('account')
    return jsonify(bank_service.get_history(account_id))


@app.route('/nodes/add', methods=['POST'])
def add_node():
    data = request.get_json()
    if not data or 'node_url' not in data:
        return jsonify({'success': False, 'error': 'node_url is required'}), 400
    
    bank_service.add_node(data['node_url'])
    return jsonify({'success': True, 'message': 'Node added'})


@app.route('/nodes/remove', methods=['POST'])
def remove_node():
    data = request.get_json()
    if not data or 'node_url' not in data:
        return jsonify({'success': False, 'error': 'node_url is required'}), 400
    
    bank_service.remove_node(data['node_url'])
    return jsonify({'success': True, 'message': 'Node removed'})


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    nodes = sys.argv[2:] if len(sys.argv) > 2 else []
    app = create_app(nodes)
    app.run(host='0.0.0.0', port=port, debug=False)