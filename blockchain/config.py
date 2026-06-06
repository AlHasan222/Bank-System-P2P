"""Configuration for the blockchain network."""
import os


class Config:
    POW_DIFFICULTY = 4
    POW_MAX_ITERATIONS = 10000000
    
    BLOCKCHAIN_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'blockchain.db')
    
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 5000
    
    NODE_TIMEOUT = 5
    SYNC_INTERVAL = 30
    
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}