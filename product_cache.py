# product_cache.py
import time
import threading
from typing import Dict, Any, Optional, List
from collections import OrderedDict
import hashlib
import logging
from config_manager import config

class ProductCache:
    """Cache inteligente LRU (Least Recently Used) para produtos"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.cache_enabled = config.get('SYSTEM', 'cache_enabled').lower() == 'true'
        self.cache_ttl = int(config.get('SYSTEM', 'cache_ttl'))
        self.max_size = 1000  # Máximo de itens no cache
        
        # LRU Cache usando OrderedDict
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.last_cleanup = time.time()
        self.cleanup_interval = 60  # segundos
        
        # Cache por código de barras e ID
        self.code_cache = {}
        self.id_cache = {}
        
        # Configurar logging
        self.logger = logging.getLogger('ProductCache')
        self._setup_logging()
    
    def _setup_logging(self):
        """Configura sistema de logs"""
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/cache.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _generate_key(self, product_code: str) -> str:
        """Gera chave de cache única"""
        return hashlib.md5(product_code.encode()).hexdigest()
    
    def get(self, product_code: str) -> Optional[Dict[str, Any]]:
        """Obtém produto do cache"""
        if not self.cache_enabled:
            return None
        
        key = self._generate_key(product_code)
        
        if key in self.cache:
            product_data, timestamp = self.cache[key]
            
            # Verifica se o cache expirou
            if time.time() - timestamp > self.cache_ttl:
                del self.cache[key]
                del self.code_cache[product_code]
                self.logger.debug(f"Cache expirado para produto: {product_code}")
                self.misses += 1
                return None
            
            # Move para o final (mais recente)
            self.cache.move_to_end(key)
            self.hits += 1
            self.logger.debug(f"Cache hit para produto: {product_code}")
            return product_data
        
        self.misses += 1
        return None
    
    def get_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Obtém produto do cache por ID"""
        if product_id in self.id_cache:
            product_code = self.id_cache[product_id]
            return self.get(product_code)
        return None
    
    def set(self, product_code: str, product_data: Dict[str, Any]):
        """Armazena produto no cache"""
        if not self.cache_enabled:
            return
        
        key = self._generate_key(product_code)
        
        # Remove item mais antigo se cache está cheio
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            oldest_product_code = self._get_product_code_from_key(oldest_key)
            
            if oldest_product_code in self.code_cache:
                del self.code_cache[oldest_product_code]
            
            # Remove do id_cache também
            product_id = self.cache[oldest_key][0].get('id')
            if product_id and product_id in self.id_cache:
                del self.id_cache[product_id]
            
            del self.cache[oldest_key]
            self.logger.debug(f"Removido item antigo do cache: {oldest_product_code}")
        
        # Adiciona ao cache
        self.cache[key] = (product_data, time.time())
        self.code_cache[product_code] = key
        
        # Adiciona ao id_cache
        if 'id' in product_data:
            self.id_cache[product_data['id']] = product_code
        
        # Move para o final (mais recente)
        self.cache.move_to_end(key)
        
        # Limpeza periódica
        self._periodic_cleanup()
    
    def _get_product_code_from_key(self, key: str) -> Optional[str]:
        """Obtém código do produto a partir da chave de cache"""
        for code, cache_key in self.code_cache.items():
            if cache_key == key:
                return code
        return None
    
    def _periodic_cleanup(self):
        """Limpeza periódica de itens expirados"""
        current_time = time.time()
        
        if current_time - self.last_cleanup > self.cleanup_interval:
            expired_keys = []
            
            for key, (product_data, timestamp) in self.cache.items():
                if current_time - timestamp > self.cache_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                product_code = self._get_product_code_from_key(key)
                if product_code and product_code in self.code_cache:
                    del self.code_cache[product_code]
                
                product_id = self.cache[key][0].get('id')
                if product_id and product_id in self.id_cache:
                    del self.id_cache[product_id]
                
                del self.cache[key]
            
            if expired_keys:
                self.logger.info(f"Limpeza de cache: removidos {len(expired_keys)} itens expirados")
            
            self.last_cleanup = current_time
    
    def invalidate(self, product_code: str = None, product_id: int = None):
        """Remove item do cache"""
        if product_code:
            key = self._generate_key(product_code)
            if key in self.cache:
                del self.cache[key]
            
            if product_code in self.code_cache:
                del self.code_cache[product_code]
        
        if product_id and product_id in self.id_cache:
            product_code = self.id_cache[product_id]
            self.invalidate(product_code)
    
    def clear(self):
        """Limpa todo o cache"""
        self.cache.clear()
        self.code_cache.clear()
        self.id_cache.clear()
        self.hits = 0
        self.misses = 0
        self.logger.info("Cache limpo completamente")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'enabled': self.cache_enabled,
            'size': len(self.cache),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': f"{hit_rate:.2f}%",
            'ttl': self.cache_ttl,
            'last_cleanup': time.strftime('%H:%M:%S', time.localtime(self.last_cleanup))
        }
    
    def preload_popular_products(self, product_codes: List[str], 
                                connection_manager = None):
        """Pré-carrega produtos populares no cache"""
        if not self.cache_enabled or not connection_manager:
            return
        
        from database import DatabaseManager
        
        db = DatabaseManager(connection_manager)
        
        for product_code in product_codes:
            if not self.get(product_code):
                product = db.get_product_by_code(product_code)
                if product:
                    self.set(product_code, product)
        
        self.logger.info(f"Pré-carregados {len(product_codes)} produtos no cache")

# Instância global
product_cache = ProductCache()