"""Flask application factory."""
import logging
from flask import Flask, request, jsonify
from blockchain.node import Node
from blockchain.config import Config
from api.routes import bp, init_routes
from api.errors import APIError, handle_api_error, handle_generic_error


def create_app(blockchain_node: Node) -> Flask:
    app = Flask(__name__)
    
    app.config['JSON_SORT_KEYS'] = False
    
    init_routes(blockchain_node)
    app.register_blueprint(bp)
    
    app.register_error_handler(APIError, handle_api_error)
    app.register_error_handler(Exception, handle_generic_error)
    
    @app.route('/')
    def index():
        return jsonify({
            'success': True,
            'service': 'Blockchain P2P Bank Mirror System',
            'node': blockchain_node.url,
            'endpoints': {
                'health': '/health',
                'chain': '/chain',
                'chain_by_index': '/chain/<index>',
                'validate': '/validate',
                'new_transaction': 'POST /transactions/new',
                'pending_transactions': '/transactions/pending',
                'mine': '/mine',
                'register_nodes': 'POST /nodes/register',
                'nodes': '/nodes',
                'resolve': '/nodes/resolve',
                'info': '/info'
            }
        })
    
    @app.before_request
    def log_request():
        logging.getLogger(__name__).debug(f"{request.method} {request.path}")
    
    return app


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else Config.DEFAULT_PORT
    node = Node(port=port)
    node.start()
    
    app = create_app(node)
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    finally:
        node.stop()