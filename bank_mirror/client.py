"""Bank Mirror CLI client."""
import sys
import requests
import json
from typing import Optional


class BankMirrorClient:
    def __init__(self, server_url: str = 'http://localhost:8000'):
        self.server_url = server_url.rstrip('/')

    def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        url = f"{self.server_url}{endpoint}"
        try:
            if method == 'GET':
                response = requests.get(url, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=10)
            else:
                return {'success': False, 'error': f'Unsupported method: {method}'}
            
            return response.json()
        except requests.exceptions.ConnectionError:
            return {'success': False, 'error': f'Cannot connect to server at {self.server_url}'}
        except requests.exceptions.Timeout:
            return {'success': False, 'error': 'Request timed out'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def health(self) -> dict:
        return self._request('GET', '/health')

    def deposit(self, from_account: str, amount: float) -> dict:
        return self._request('POST', '/send/deposit', {
            'from_account': from_account,
            'amount': amount
        })

    def withdrawal(self, from_account: str, amount: float) -> dict:
        return self._request('POST', '/send/withdrawal', {
            'from_account': from_account,
            'amount': amount
        })

    def transfer(self, from_account: str, to_account: str, amount: float) -> dict:
        return self._request('POST', '/send/transfer', {
            'from_account': from_account,
            'to_account': to_account,
            'amount': amount
        })

    def custom(self, from_account: str, amount: float, tx_type: str, to_account: str = None) -> dict:
        data = {'from_account': from_account, 'amount': amount, 'type': tx_type}
        if to_account:
            data['to_account'] = to_account
        return self._request('POST', '/send/custom', data)

    def status(self) -> dict:
        return self._request('GET', '/status')

    def history(self, account: str = None) -> dict:
        params = f"?account={account}" if account else ""
        return self._request('GET', f'/history{params}')

    def add_node(self, node_url: str) -> dict:
        return self._request('POST', '/nodes/add', {'node_url': node_url})

    def remove_node(self, node_url: str) -> dict:
        return self._request('POST', '/nodes/remove', {'node_url': node_url})


def print_result(result: dict):
    if result.get('success'):
        print(json.dumps(result, indent=2))
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        if 'details' in result:
            print(f"Details: {result['details']}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m bank_mirror.client <command> [args...]")
        print("\nCommands:")
        print("  health                    - Check server health")
        print("  deposit <account> <amt>   - Send deposit")
        print("  withdrawal <account> <amt> - Send withdrawal")
        print("  transfer <from> <to> <amt> - Send transfer")
        print("  custom <account> <amt> <type> [to] - Custom transaction")
        print("  status                    - Get server status")
        print("  history [account]         - Get transaction history")
        print("  add-node <url>            - Add blockchain node")
        print("  remove-node <url>         - Remove blockchain node")
        sys.exit(1)

    server_url = 'http://localhost:8000'
    client = BankMirrorClient(server_url)

    command = sys.argv[1]

    if command == 'health':
        print_result(client.health())
    
    elif command == 'deposit':
        if len(sys.argv) < 4:
            print("Usage: deposit <account> <amount>")
            sys.exit(1)
        print_result(client.deposit(sys.argv[2], float(sys.argv[3])))
    
    elif command == 'withdrawal':
        if len(sys.argv) < 4:
            print("Usage: withdrawal <account> <amount>")
            sys.exit(1)
        print_result(client.withdrawal(sys.argv[2], float(sys.argv[3])))
    
    elif command == 'transfer':
        if len(sys.argv) < 5:
            print("Usage: transfer <from> <to> <amount>")
            sys.exit(1)
        print_result(client.transfer(sys.argv[2], sys.argv[3], float(sys.argv[4])))
    
    elif command == 'custom':
        if len(sys.argv) < 5:
            print("Usage: custom <account> <amount> <type> [to_account]")
            sys.exit(1)
        to_account = sys.argv[5] if len(sys.argv) > 5 else None
        print_result(client.custom(sys.argv[2], float(sys.argv[3]), sys.argv[4], to_account))
    
    elif command == 'status':
        print_result(client.status())
    
    elif command == 'history':
        account = sys.argv[2] if len(sys.argv) > 2 else None
        print_result(client.history(account))
    
    elif command == 'add-node':
        if len(sys.argv) < 3:
            print("Usage: add-node <url>")
            sys.exit(1)
        print_result(client.add_node(sys.argv[2]))
    
    elif command == 'remove-node':
        if len(sys.argv) < 3:
            print("Usage: remove-node <url>")
            sys.exit(1)
        print_result(client.remove_node(sys.argv[2]))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == '__main__':
    main()