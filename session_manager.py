# session_manager.py
import time
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from config_manager import config
from connection_manager import connection_pool

class SessionManager:
    """Gerenciador de sessões do PDV"""
    
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
        self.session_timeout = int(config.get('AUTH', 'session_timeout', fallback='3600'))
        
        # Configurar logging
        self.logger = logging.getLogger('SessionManager')
        self._setup_logging()
        
        # Iniciar limpeza periódica
        self._start_cleanup_thread()
    
    def _setup_logging(self):
        """Configurar sistema de logs"""
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/sessions.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def create_caixa_session(self, pdv_id: int, usuario_id: int, 
                           loja_id: int, valor_abertura: float = 0) -> Optional[int]:
        """Criar nova sessão de caixa"""
        try:
            # Verificar se já existe sessão aberta para este PDV
            query_check = """
            SELECT id FROM caixa_sessao 
            WHERE pdv_id = %s AND estado = 'ABERTA'
            """
            
            result = connection_pool.execute_query(
                query_check, (pdv_id,), fetchone=True
            )
            
            if result:
                self.logger.warning(f"Já existe sessão aberta para PDV {pdv_id}")
                return None
            
            # Obter sessão da loja
            query_loja = """
            SELECT id FROM loja_sessao 
            WHERE loja_id = %s AND estado = 'ABERTA'
            ORDER BY data_abertura DESC LIMIT 1
            """
            
            loja_sessao = connection_pool.execute_query(
                query_loja, (loja_id,), fetchone=True
            )
            
            if not loja_sessao:
                # Criar sessão da loja se não existir
                query_create_loja = """
                INSERT INTO loja_sessao (loja_id, usuario_abertura_id, estado)
                VALUES (%s, %s, 'ABERTA')
                """
                
                loja_sessao_id = connection_pool.execute_query(
                    query_create_loja, (loja_id, usuario_id)
                )
                loja_sessao = {'id': loja_sessao_id}
            
            # Criar sessão do caixa
            query_caixa = """
            INSERT INTO caixa_sessao 
            (loja_sessao_id, pdv_id, usuario_id, valor_abertura, estado)
            VALUES (%s, %s, %s, %s, 'ABERTA')
            """
            
            caixa_sessao_id = connection_pool.execute_query(
                query_caixa, (loja_sessao['id'], pdv_id, usuario_id, valor_abertura)
            )
            
            # Registrar no cache local
            self.active_sessions[pdv_id] = {
                'session_id': caixa_sessao_id,
                'pdv_id': pdv_id,
                'usuario_id': usuario_id,
                'loja_id': loja_id,
                'valor_abertura': valor_abertura,
                'data_abertura': datetime.now().isoformat(),
                'total_vendas': 0,
                'total_sangrias': 0,
                'total_reforcos': 0,
                'estado': 'ABERTA'
            }
            
            self.logger.info(f"Sessão criada: PDV {pdv_id}, Usuário {usuario_id}")
            return caixa_sessao_id
            
        except Exception as e:
            self.logger.error(f"Erro ao criar sessão: {e}")
            return None
    
    # session_manager.py - Melhorar método close_caixa_session

    def close_caixa_session(self, pdv_id: int, usuario_id: int, 
                           valor_contado: float, observacoes: str = "") -> bool:
        """Fechar sessão de caixa - VERSÃO MELHORADA"""
        try:
            if pdv_id not in self.active_sessions:
                self.logger.error(f"Sessão não encontrada para PDV {pdv_id}")
                return False
            
            session_data = self.active_sessions[pdv_id]
            
            # Calcular valores teóricos
            valor_teorico = (
                session_data['valor_abertura'] +
                session_data['total_vendas'] -
                session_data['total_sangrias'] +
                session_data['total_reforcos']
            )
            
            diferenca = valor_contado - valor_teorico
            
            # Atualizar banco de dados
            query = """
            UPDATE caixa_sessao 
            SET data_fecho = NOW(),
                valor_fecho = %s,
                valor_teorico = %s,
                valor_contado = %s,
                diferenca = %s,
                total_vendas = %s,
                total_sangrias = %s,
                total_reforcos = %s,
                usuario_fecho_id = %s,
                estado = 'FECHADA'
            WHERE pdv_id = %s AND estado = 'ABERTA'
            """
            
            connection_pool.execute_query(query, (
                valor_contado, valor_teorico, valor_contado, diferenca,
                session_data['total_vendas'], session_data['total_sangrias'],
                session_data['total_reforcos'], usuario_id, pdv_id
            ))
            
            # Remover do cache
            del self.active_sessions[pdv_id]
            
            # Registrar log
            self.logger.info(
                f"Sessão fechada - PDV: {pdv_id}, "
                f"Teórico: {valor_teorico:.2f}, "
                f"Contado: {valor_contado:.2f}, "
                f"Diferença: {diferenca:.2f}"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao fechar sessão: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _registrar_fecho_detalhe(self, pdv_id: int, session_data: Dict[str, Any]):
        """Registrar detalhes do fecho por forma de pagamento"""
        try:
            # Obter totais por forma de pagamento
            query_totais = """
            SELECT forma_pagamento_id, SUM(total_pago) as valor_sistema
            FROM vendas 
            WHERE pdv_id = %s 
                AND DATE(data_emissao) = DATE(NOW())
                AND estado = 'EMITIDO'
            GROUP BY forma_pagamento_id
            """
            
            totais = connection_pool.execute_query(query_totais, (pdv_id,), fetchall=True)
            
            for total in totais:
                query_detalhe = """
                INSERT INTO caixa_fecho_detalhe 
                (sessao_id, forma_pagamento_id, valor_sistema)
                VALUES (%s, %s, %s)
                """
                
                connection_pool.execute_query(
                    query_detalhe, 
                    (session_data['session_id'], total['forma_pagamento_id'], total['valor_sistema'])
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao registrar detalhes: {e}")
    
    def get_active_session(self, pdv_id: int) -> Optional[Dict[str, Any]]:
        """Obter sessão ativa do PDV"""
        return self.active_sessions.get(pdv_id)
    
    def update_session_totals(self, pdv_id: int, venda_valor: float = 0,
                            sangria_valor: float = 0, reforco_valor: float = 0):
        """Atualizar totais da sessão"""
        if pdv_id in self.active_sessions:
            session = self.active_sessions[pdv_id]
            session['total_vendas'] += venda_valor
            session['total_sangrias'] += sangria_valor
            session['total_reforcos'] += reforco_valor
    
    def _start_cleanup_thread(self):
        """Iniciar thread para limpar sessões expiradas"""
        def cleanup_worker():
            while True:
                time.sleep(300)  # Verificar a cada 5 minutos
                self._cleanup_expired_sessions()
        
        thread = threading.Thread(target=cleanup_worker, daemon=True)
        thread.start()
    
    def _cleanup_expired_sessions(self):
        """Limpar sessões expiradas do cache"""
        current_time = datetime.now()
        expired_sessions = []
        
        for pdv_id, session in self.active_sessions.items():
            session_time = datetime.fromisoformat(session['data_abertura'])
            if (current_time - session_time).seconds > self.session_timeout:
                expired_sessions.append(pdv_id)
        
        for pdv_id in expired_sessions:
            self.logger.warning(f"Sessão expirada removida: PDV {pdv_id}")
            del self.active_sessions[pdv_id]
    
    def get_session_summary(self, pdv_id: int) -> Dict[str, Any]:
        """Obter resumo da sessão"""
        if pdv_id in self.active_sessions:
            session = self.active_sessions[pdv_id]
            return {
                'valor_abertura': session['valor_abertura'],
                'total_vendas': session['total_vendas'],
                'total_sangrias': session['total_sangrias'],
                'total_reforcos': session['total_reforcos'],
                'saldo_atual': (
                    session['valor_abertura'] +
                    session['total_vendas'] -
                    session['total_sangrias'] +
                    session['total_reforcos']
                ),
                'data_abertura': session['data_abertura']
            }
        return {}

# Instância global
session_manager = SessionManager()