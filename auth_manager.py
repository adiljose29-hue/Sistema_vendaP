# auth_manager.py
import hashlib
import time
import threading
from typing import Dict, Any, Optional, Tuple
import logging
from config_manager import config
from connection_manager import connection_pool

class AuthManager:
    """Gerenciador avançado de autenticação e sessões"""
    
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
        self.active_sessions = {}
        self.login_attempts = {}
        self.max_attempts = int(config.get('AUTH', 'max_login_attempts'))
        self.session_timeout = int(config.get('AUTH', 'session_timeout'))
        self.password_length = int(config.get('AUTH', 'password_length'))
        self.worker_id_length = int(config.get('AUTH', 'worker_id_length'))
        
        # Configurar logging
        self.logger = logging.getLogger('AuthManager')
        self._setup_logging()
        
        # Iniciar limpeza periódica de sessões
        self._start_session_cleaner()
    
    def _setup_logging(self):
        """Configura sistema de logs"""
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/auth.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _hash_password(self, password: str) -> str:
        """Cria hash da senha (simples para início)"""
        # TODO: Implementar hash mais seguro (bcrypt) em produção
        return hashlib.sha256(password.encode()).hexdigest()
    
    # auth_manager.py - Correção na validação de senha
    def validate_credentials(self, worker_id: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Valida credenciais do usuário"""
        self.logger.info(f"Tentativa de login - Worker ID: {worker_id}, Senha: {'*' * len(password)}")
        
        # Validação básica
        if not worker_id.isdigit() or len(worker_id) != self.worker_id_length:
            self.logger.warning(f"Worker ID inválido: {worker_id}")
            return False, None
        
        if not password.isdigit() or len(password) != self.password_length:
            self.logger.warning(f"Senha inválida para worker {worker_id}")
            return False, None
        
        # Verificar tentativas de login
        attempts_key = f"worker_{worker_id}"
        if attempts_key in self.login_attempts:
            attempts, last_attempt = self.login_attempts[attempts_key]
            if attempts >= self.max_attempts:
                if time.time() - last_attempt < 300:
                    self.logger.warning(f"Worker {worker_id} bloqueado por excesso de tentativas")
                    return False, {"error": "bloqueado", "message": "Conta temporariamente bloqueada"}
        
        # Consultar banco de dados
        try:
            query = """
            SELECT u.id, u.numero_trabalhador, u.nome, u.username, u.senha, 
                   u.perfil, u.per_venda, u.ativo, u.loja_id,
                   l.codigo as loja_codigo, l.nome as loja_nome
            FROM usuarios u
            LEFT JOIN loja l ON u.loja_id = l.id
            WHERE u.numero_trabalhador = %s AND u.ativo = 1
            """
            
            self.logger.info(f"Executando query para worker_id: {worker_id}")
            result = connection_pool.execute_query(query, (int(worker_id),), fetchone=True)
            
            if not result:
                self._record_login_attempt(worker_id, False)
                self.logger.warning(f"Worker ID não encontrado: {worker_id}")
                return False, None
            
            self.logger.info(f"Usuário encontrado: {result['nome']}, Senha no BD: {result['senha']}")
            
            # Verificar senha - IMPORTANTE: Comparar strings
            senha_bd = str(result['senha'])
            senha_digitada = str(password)
            
            self.logger.info(f"Comparando senhas - BD: '{senha_bd}' vs Digitada: '{senha_digitada}'")
            self.logger.info(f"Tipos - BD: {type(senha_bd)}, Digitada: {type(senha_digitada)}")
            self.logger.info(f"Iguais? {senha_bd == senha_digitada}")
            
            if senha_bd != senha_digitada:
                self._record_login_attempt(worker_id, False)
                self.logger.warning(f"Senha incorreta para worker {worker_id}")
                return False, None
            
            # Login bem-sucedido
            self._record_login_attempt(worker_id, True)
            self.logger.info(f"Login bem-sucedido para worker {worker_id}")
            
            # Remover senha do resultado
            del result['senha']
            
            return True, result
            
        except Exception as e:
            self.logger.error(f"Erro na validação de credenciais: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, None
    
    def _record_login_attempt(self, worker_id: str, success: bool):
        """Registra tentativa de login"""
        attempts_key = f"worker_{worker_id}"
        
        if success:
            if attempts_key in self.login_attempts:
                del self.login_attempts[attempts_key]
        else:
            if attempts_key in self.login_attempts:
                attempts, _ = self.login_attempts[attempts_key]
                self.login_attempts[attempts_key] = (attempts + 1, time.time())
            else:
                self.login_attempts[attempts_key] = (1, time.time())
    
    def create_session(self, user_data: Dict[str, Any]) -> str:
        """Cria nova sessão para usuário"""
        session_id = hashlib.sha256(f"{user_data['id']}_{time.time()}".encode()).hexdigest()[:32]
        
        session_data = {
            'session_id': session_id,
            'user_id': user_data['id'],
            'worker_id': user_data['numero_trabalhador'],
            'name': user_data['nome'],
            'profile': user_data['perfil'],
            'per_venda': user_data['per_venda'],
            'loja_id': user_data['loja_id'],
            'loja_codigo': user_data.get('loja_codigo', ''),
            'loja_nome': user_data.get('loja_nome', ''),
            'login_time': time.time(),
            'last_activity': time.time(),
            'active': True
        }
        
        self.active_sessions[session_id] = session_data
        self.logger.info(f"Sessão criada para worker {user_data['numero_trabalhador']}: {session_id}")
        
        return session_id
    
    def validate_session(self, session_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Valida sessão existente"""
        if session_id not in self.active_sessions:
            return False, None
        
        session = self.active_sessions[session_id]
        
        # Verificar timeout
        if time.time() - session['last_activity'] > self.session_timeout:
            self.logger.info(f"Sessão expirada: {session_id}")
            self.destroy_session(session_id)
            return False, None
        
        # Atualizar última atividade
        session['last_activity'] = time.time()
        self.active_sessions[session_id] = session
        
        return True, session
    
    def destroy_session(self, session_id: str):
        """Destrói sessão"""
        if session_id in self.active_sessions:
            user_data = self.active_sessions[session_id]
            self.logger.info(f"Sessão destruída para worker {user_data['worker_id']}: {session_id}")
            del self.active_sessions[session_id]
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Retorna todas as sessões ativas"""
        return self.active_sessions.copy()
    
    def _start_session_cleaner(self):
        """Inicia thread para limpar sessões expiradas"""
        def cleaner():
            while True:
                time.sleep(60)  # Verifica a cada minuto
                self._clean_expired_sessions()
        
        thread = threading.Thread(target=cleaner, daemon=True)
        thread.start()
    
    def _clean_expired_sessions(self):
        """Remove sessões expiradas"""
        current_time = time.time()
        expired_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if current_time - session['last_activity'] > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            self.destroy_session(session_id)
        
        if expired_sessions:
            self.logger.info(f"Limpeza de sessões: removidas {len(expired_sessions)} sessões expiradas")
    
    def get_user_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtém informações do usuário a partir da sessão"""
        valid, session = self.validate_session(session_id)
        if valid:
            return {
                'worker_id': session['worker_id'],
                'name': session['name'],
                'profile': session['profile'],
                'loja_codigo': session['loja_codigo'],
                'loja_nome': session['loja_nome']
            }
        return None

# Instância global
auth_manager = AuthManager()