#!/usr/bin/env python3

import subprocess
import time
import sys
import os
import threading
import requests
import json


class DemoRunner:
    def __init__(self):
        self.processes = []
        self.nodes = [
            {'port': 5000, 'url': 'http://localhost:5000'},
            {'port': 5001, 'url': 'http://localhost:5001'},
            {'port': 5002, 'url': 'http://localhost:5002'}
        ]
        self.bank_port = 8000
        self.bank_url = f'http://localhost:{self.bank_port}'

    def start_node(self, port):
        """Start a blockchain node as subprocess."""
        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd()
        proc = subprocess.Popen([
            sys.executable, '-m', 'api.app', str(port)
        ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc

    def start_bank_server(self):
        """Start bank mirror server."""
        node_urls = ' '.join([n['url'] for n in self.nodes])
        env = os.environ.copy()
        env['PYTHONPATH'] = os.getcwd()
        proc = subprocess.Popen([
            sys.executable, '-m', 'bank_mirror.server', str(self.bank_port)
        ] + [n['url'] for n in self.nodes],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc

    def wait_for_health(self, url, timeout=30):
        """Wait for node to become healthy."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                resp = requests.get(f'{url}/health', timeout=2)
                if resp.status_code == 200:
                    return True
            except:
                pass
            time.sleep(0.5)
        return False

    def register_peers(self):
        """Register all nodes as peers of each other."""
        print("\n=== Registering Peer Nodes ===")
        for node in self.nodes:
            other_nodes = [n['url'] for n in self.nodes if n['url'] != node['url']]
            try:
                resp = requests.post(
                    f"{node['url']}/nodes/register",
                    json={'nodes': other_nodes},
                    timeout=5
                )
                if resp.status_code == 201:
                    print(f"  {node['url']}: Registered {len(other_nodes)} peers")
                else:
                    print(f"  {node['url']}: Failed - {resp.text}")
            except Exception as e:
                print(f"  {node['url']}: Error - {e}")

    def send_bank_transactions(self):
        """Send transactions via bank mirror."""
        print("\n=== Sending Bank Transactions ===")
        transactions = [
            ('deposit', {'from_account': 'ACC001', 'amount': 1000}),
            ('deposit', {'from_account': 'ACC002', 'amount': 500}),
            ('transfer', {'from_account': 'ACC001', 'to_account': 'ACC002', 'amount': 200}),
            ('withdrawal', {'from_account': 'ACC002', 'amount': 100}),
            ('deposit', {'from_account': 'ACC003', 'amount': 300}),
        ]
        
        for tx_type, data in transactions:
            try:
                resp = requests.post(
                    f"{self.bank_url}/send/{tx_type}",
                    json=data,
                    timeout=5
                )
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get('success'):
                        print(f"  {tx_type.upper()}: {data} -> Success")
                    else:
                        print(f"  {tx_type.upper()}: {data} -> Failed: {result.get('error')}")
                else:
                    print(f"  {tx_type.upper()}: HTTP {resp.status_code}")
            except Exception as e:
                print(f"  {tx_type.upper()}: Error - {e}")
            time.sleep(0.5)

    def mine_blocks(self):
        """Mine blocks on each node."""
        print("\n=== Mining Blocks ===")
        for node in self.nodes:
            try:
                resp = requests.get(f"{node['url']}/mine", timeout=30)
                if resp.status_code == 201:
                    result = resp.json()
                    block = result.get('block', {})
                    print(f"  {node['url']}: Mined block #{block.get('index')} with {len(block.get('transactions', []))} txs")
                elif resp.status_code == 409:
                    print(f"  {node['url']}: No pending transactions to mine")
                else:
                    print(f"  {node['url']}: Mining failed - {resp.text}")
            except Exception as e:
                print(f"  {node['url']}: Error - {e}")

    def sync_chains(self):
        """Trigger consensus on all nodes."""
        print("\n=== Synchronizing Chains (Consensus) ===")
        for node in self.nodes:
            try:
                resp = requests.get(f"{node['url']}/nodes/resolve", timeout=10)
                if resp.status_code == 200:
                    result = resp.json()
                    if result.get('replaced'):
                        print(f"  {node['url']}: Chain REPLACED (length: {len(result.get('chain', []))})")
                    else:
                        print(f"  {node['url']}: Chain authoritative (length: {len(result.get('chain', []))})")
                else:
                    print(f"  {node['url']}: Sync failed")
            except Exception as e:
                print(f"  {node['url']}: Error - {e}")

    def validate_chains(self):
        """Validate chain integrity on all nodes."""
        print("\n=== Validating Chain Integrity ===")
        for node in self.nodes:
            try:
                resp = requests.get(f"{node['url']}/validate", timeout=5)
                if resp.status_code == 200:
                    result = resp.json()
                    status = "VALID" if result.get('valid') else "INVALID"
                    print(f"  {node['url']}: {status} - {result.get('block_count')} blocks")
                    if result.get('issues'):
                        for issue in result['issues']:
                            print(f"    Issue: {issue}")
                else:
                    print(f"  {node['url']}: Validation failed")
            except Exception as e:
                print(f"  {node['url']}: Error - {e}")

    def show_chain_info(self):
        """Display chain info from all nodes."""
        print("\n=== Chain Information ===")
        for node in self.nodes:
            try:
                resp = requests.get(f"{node['url']}/chain", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"  {node['url']}: {data['length']} blocks")
                    for block in data['chain'][-2:]:  # Show last 2 blocks
                        print(f"    Block #{block['index']}: {block['hash'][:16]}... ({len(block['transactions'])} txs)")
            except Exception as e:
                print(f"  {node['url']}: Error - {e}")

    def test_persistence(self):
        """Test persistence by restarting a node."""
        print("\n=== Testing Persistence (Restart Node 1) ===")
        
        # Stop node 1
        print("  Stopping node 1...")
        self.processes[0].terminate()
        self.processes[0].wait(timeout=5)
        
        # Restart node 1
        print("  Restarting node 1...")
        self.processes[0] = self.start_node(5000)
        
        # Wait for health
        if self.wait_for_health('http://localhost:5000'):
            print("  Node 1 restarted successfully")
            
            # Check chain recovered
            try:
                resp = requests.get('http://localhost:5000/chain', timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"  Chain recovered: {data['length']} blocks")
            except Exception as e:
                print(f"  Error checking chain: {e}")
        else:
            print("  Node 1 failed to restart")

    def run(self):
        """Run complete demo workflow."""
        print("=" * 60)
        print("BLOCKCHAIN P2P BANK MIRROR SYSTEM - DEMO")
        print("=" * 60)
        
        # Start blockchain nodes
        print("\n[1/8] Starting 3 Blockchain Nodes...")
        for node in self.nodes:
            proc = self.start_node(node['port'])
            self.processes.append(proc)
            print(f"  Started node on port {node['port']}")
        
        # Wait for nodes to be healthy
        print("\n[2/8] Waiting for nodes to be ready...")
        for node in self.nodes:
            if self.wait_for_health(node['url']):
                print(f"  {node['url']}: READY")
            else:
                print(f"  {node['url']}: TIMEOUT")
                self.cleanup()
                return
        
        # Start bank server
        print("\n[3/8] Starting Bank Mirror Server...")
        bank_proc = self.start_bank_server()
        self.processes.append(bank_proc)
        
        if self.wait_for_health(self.bank_url):
            print(f"  Bank server ready at {self.bank_url}")
        else:
            print("  Bank server failed to start")
            self.cleanup()
            return
        
        # Register peers
        print("\n[4/8] Registering Peer Nodes...")
        self.register_peers()
        time.sleep(2)
        
        # Send transactions
        print("\n[5/8] Sending Bank Transactions...")
        self.send_bank_transactions()
        time.sleep(2)
        
        # Mine blocks
        print("\n[6/8] Mining Blocks...")
        self.mine_blocks()
        time.sleep(3)
        
        # Sync chains
        print("\n[7/8] Synchronizing Chains (Consensus)...")
        self.sync_chains()
        time.sleep(2)
        
        # Validate
        print("\n[8/8] Validating Chain Integrity...")
        self.validate_chains()
        
        # Show info
        self.show_chain_info()
        
        # Test persistence
        self.test_persistence()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETE")
        print("=" * 60)
        print("\nNodes still running. Press Ctrl+C to stop all.")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.cleanup()

    def cleanup(self):
        """Stop all processes."""
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except:
                try:
                    proc.kill()
                except:
                    pass


def main():
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Install dependencies if needed
    try:
        import flask
        import requests
    except ImportError:
        print("Installing dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
    
    demo = DemoRunner()
    demo.run()


if __name__ == '__main__':
    main()