"""Consensus mechanism for the blockchain network."""
import logging
import requests
from typing import List, Optional, Set
from blockchain.block import Block
from blockchain.blockchain import Blockchain
from blockchain.config import Config


logger = logging.getLogger(__name__)


class ConsensusManager:
    def __init__(self, blockchain: Blockchain):
        self.blockchain = blockchain

    def sync_chain(self) -> bool:
        if not self.blockchain.nodes:
            logger.info("No peer nodes to sync with")
            return False
        
        replaced = self.blockchain.resolve_conflicts()
        
        if replaced:
            logger.info("Chain synchronized with peers")
        else:
            logger.info("Chain is up to date with peers")
        
        return replaced

    def announce_new_block(self, block: Block) -> int:
        if not self.blockchain.nodes:
            return 0
        
        announced = 0
        block_data = block.to_dict()
        
        for node in self.blockchain.nodes:
            try:
                response = requests.post(
                    f"{node}/blocks/new",
                    json=block_data,
                    timeout=Config.NODE_TIMEOUT
                )
                if response.status_code == 201:
                    announced += 1
                    logger.debug(f"Block announced to {node}")
            except Exception as e:
                logger.warning(f"Failed to announce block to {node}: {e}")
        
        logger.info(f"New block announced to {announced}/{len(self.blockchain.nodes)} nodes")
        return announced

    def peer_health_check(self) -> dict:
        results = {}
        for node in self.blockchain.nodes:
            try:
                response = requests.get(
                    f"{node}/health",
                    timeout=Config.NODE_TIMEOUT
                )
                results[node] = response.status_code == 200
            except Exception:
                results[node] = False
        
        healthy = sum(1 for v in results.values() if v)
        logger.info(f"Peer health check: {healthy}/{len(results)} nodes healthy")
        return results

    def fetch_peer_chains(self) -> List[tuple]:
        chains = []
        for node in self.blockchain.nodes:
            try:
                response = requests.get(
                    f"{node}/chain",
                    timeout=Config.NODE_TIMEOUT
                )
                if response.status_code == 200:
                    data = response.json()
                    chain_data = data.get('chain', [])
                    length = data.get('length', 0)
                    chain = [Block.from_dict(b) for b in chain_data]
                    chains.append((node, chain, length))
            except Exception as e:
                logger.warning(f"Failed to fetch chain from {node}: {e}")
        return chains

    def validate_and_compare_chains(self, chains: List[tuple]) -> Optional[List[Block]]:
        valid_chains = []
        
        for node, chain, length in chains:
            if self.blockchain.valid_chain(chain):
                valid_chains.append((node, chain, length))
                logger.debug(f"Valid chain from {node}: length={length}")
            else:
                logger.warning(f"Invalid chain from {node} rejected")
        
        if not valid_chains:
            return None
        
        valid_chains.sort(key=lambda x: x[2], reverse=True)
        longest = valid_chains[0]
        
        if longest[2] > len(self.blockchain.chain):
            logger.info(f"Adopting longer chain from {longest[0]}: {longest[2]} > {len(self.blockchain.chain)}")
            return longest[1]
        
        return None