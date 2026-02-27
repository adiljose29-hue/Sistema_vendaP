# connection_manager.py
import mysql.connector
from mysql.connector import Error, pooling
import threading
import time
import logging
from typing import Optional, Dict, Any
from config_manager import config

class ConnectionPoolManager:
    """Gerenciador avançado de pool de conexões MySQL"""
    
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
        self.pool = None
        self.connection_status = False
        self.last_check = time.time()
        self.check_interval = 30  # segundos
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config.get_database_config()['reconnect_attempts']
        self.reconnect_delay = config.get_database_config()['reconnect_delay']
        
        # Configurar logging
        self.logger = logging.getLogger('ConnectionManager')
        self._setup_logging()
        
        # Inicializar pool
        self._initialize_pool()
    
    def _setup_logging(self):
        """Configura sistema de logs"""
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/connection.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _initialize_pool(self):
        """Inicializa pool de conexões"""
        db_config = config.get_database_config()
        
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="pdv_pool",
                pool_size=10,
                pool_reset_session=True,
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['username'],
                password=db_config['password'],
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci',
                autocommit=True,
                connection_timeout=10,
                buffered=True
            )
            
            self.connection_status = True
            self.reconnect_attempts = 0
            self.logger.info("Pool de conexões inicializado com sucesso")
            
        except Error as e:
            self.connection_status = False
            self.logger.error(f"Erro ao inicializar pool: {e}")
            self._handle_connection_error()
    
    def get_connection(self) -> Optional[mysql.connector.connection.MySQLConnection]:
        """Obtém conexão do pool"""
        try:
            if self.pool is None:
                self._initialize_pool()
            
            if time.time() - self.last_check > self.check_interval:
                self._check_connection()
            
            connection = self.pool.get_connection()
            
            if connection.is_connected():
                self.connection_status = True
                return connection
            else:
                self.connection_status = False
                self.logger.warning("Conexão obtida mas não está ativa")
                self._handle_connection_error()
                return None
                
        except Error as e:
            self.connection_status = False
            self.logger.error(f"Erro ao obter conexão: {e}")
            self._handle_connection_error()
            return None
    
    def return_connection(self, connection: mysql.connector.connection.MySQLConnection):
        """Devolve conexão ao pool"""
        try:
            if connection.is_connected():
                connection.close()
        except Error as e:
            self.logger.error(f"Erro ao devolver conexão: {e}")
    
    def _check_connection(self):
        """Verifica estado da conexão"""
        self.last_check = time.time()
        
        try:
            conn = self.pool.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            
            if not self.connection_status:
                self.logger.info("Conexão restabelecida")
            
            self.connection_status = True
            self.reconnect_attempts = 0
            
        except Error as e:
            self.connection_status = False
            self.logger.error(f"Falha na verificação de conexão: {e}")
            self._handle_connection_error()
    
    def _handle_connection_error(self):
        """Lida com erro de conexão e tenta reconectar"""
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            self.logger.info(f"Tentativa de reconexão {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            
            time.sleep(self.reconnect_delay)
            self._initialize_pool()
        else:
            self.logger.error("Número máximo de tentativas de reconexão atingido")
    
    def execute_query(self, query: str, params: tuple = None, 
                     fetchone: bool = False, fetchall: bool = False):
        """Executa query com tratamento automático de conexão"""
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            if connection is None:
                raise ConnectionError("Não foi possível obter conexão")
            
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if fetchone:
                result = cursor.fetchone()
            elif fetchall:
                result = cursor.fetchall()
            else:
                result = cursor.lastrowid
            
            connection.commit()
            return result
            
        except Error as e:
            self.logger.error(f"Erro na query: {e}")
            if connection:
                connection.rollback()
            raise
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                self.return_connection(connection)
    
    def get_status(self) -> Dict[str, Any]:
        """Retorna status da conexão"""
        return {
            'connected': self.connection_status,
            'reconnect_attempts': self.reconnect_attempts,
            'max_attempts': self.max_reconnect_attempts,
            'last_check': time.strftime('%H:%M:%S', time.localtime(self.last_check)),
            'pool_size': self.pool.pool_size if self.pool else 0
        }
    
    def test_connection(self) -> bool:
        """Testa conexão com o banco de dados"""
        try:
            self._check_connection()
            return self.connection_status
        except:
            return False

# Instância global
connection_pool = ConnectionPoolManager()