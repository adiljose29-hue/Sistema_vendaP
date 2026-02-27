# caixa_manager.py
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging
from config_manager import config
from connection_manager import connection_pool

class CaixaManager:
    """Gerenciador avançado de operações de caixa (sangria e suprimento)"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.logger = logging.getLogger('CaixaManager')
        self._setup_logging()
    
    def _setup_logging(self):
        """Configurar logging"""
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/caixa.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def get_formas_pagamento_com_valor(self, sessao_id: int, pdv_id: int) -> List[Dict[str, Any]]:
        """Obter formas de pagamento com valores acumulados na sessão - VERSÃO SIMPLIFICADA"""
        try:
            # Primeiro, obter todas formas ativas
            query_formas = """
            SELECT id, nome, codigo, aceita_troco
            FROM forma_pagamento 
            WHERE ativo = 1
            ORDER BY nome
            """
            
            formas = connection_pool.execute_query(query_formas, fetchall=True)
            
            if not formas:
                self.logger.warning("Nenhuma forma de pagamento ativa encontrada")
                return []
            
            self.logger.info(f"Encontradas {len(formas)} formas de pagamento ativas")
            
            # Para cada forma, calcular valor em sistema
            for forma in formas:
                # Obter vendas do dia para esta forma e PDV
                query_vendas = """
                SELECT COALESCE(SUM(total_pago), 0) as valor_sistema
                FROM vendas 
                WHERE forma_pagamento_id = %s 
                    AND pdv_id = %s
                    AND DATE(data_emissao) = CURDATE()
                    AND estado = 'EMITIDO'
                """
                
                result = connection_pool.execute_query(
                    query_vendas, 
                    (forma['id'], pdv_id), 
                    fetchone=True
                )
                
                valor_sistema = float(result['valor_sistema']) if result else 0.0
                forma['valor_sistema'] = valor_sistema
                
                # Obter sangrias já feitas
                forma['valor_sangrias'] = float(self._get_total_sangrias_forma(sessao_id, forma['id']))
                
                # Calcular disponível
                forma['valor_disponivel'] = max(0.0, valor_sistema - forma['valor_sangrias'])
                
                self.logger.debug(f"Forma {forma['nome']}: Sistema={valor_sistema}, "
                                f"Sangrias={forma['valor_sangrias']}, "
                                f"Disponível={forma['valor_disponivel']}")
            
            # Filtrar apenas formas com valor disponível > 0 ou que seja dinheiro
            formas_filtradas = [
                f for f in formas 
                if f['valor_disponivel'] > 0 or f['codigo'] == 'DIN'
            ]
            
            self.logger.info(f"Retornando {len(formas_filtradas)} formas com valor disponível")
            return formas_filtradas
            
        except Exception as e:
            self.logger.error(f"Erro ao obter formas de pagamento: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
        
    # Verificar se o arquivo inteiro tem indentação consistente
        
    def _get_total_sangrias_forma(self, sessao_id: int, forma_pagamento_id: int) -> float:
        """Obter total de sangrias por forma de pagamento"""
        try:
            query = """
            SELECT COALESCE(SUM(cm.valor), 0) as total
            FROM caixa_movimentos cm
            WHERE cm.sessao_id = %s 
                AND cm.forma_pagamento_id = %s
                AND cm.tipo = 'SANGRIA'
            """
            
            result = connection_pool.execute_query(
                query, (sessao_id, forma_pagamento_id), fetchone=True
            )
            
            return float(result['total']) if result else 0.0
            
        except Exception as e:
            self.logger.error(f"Erro ao obter sangrias: {e}")
            return 0.0
    
    def registrar_sangria(self, sessao_id: int, pdv_id: int, usuario_id: int,
                         forma_pagamento_id: int, valor: float, 
                         valor_sistema: float = None, motivo: str = "") -> Tuple[bool, int]:
        """Registrar sangria no sistema"""
        try:
            # Se não fornecer valor_sistema, usar o valor_sistema atual
            if valor_sistema is None:
                valor_sistema = self._get_valor_sistema_forma(
                    sessao_id, forma_pagamento_id
                )
            
            # Calcular diferença
            diferenca = valor_sistema - valor
            
            # Inserir movimento principal
            query_movimento = """
            INSERT INTO caixa_movimentos 
            (sessao_id, tipo, valor, motivo, usuario_id, pdv_id, forma_pagamento_id)
            VALUES (%s, 'SANGRIA', %s, %s, %s, %s, %s)
            """
            
            movimento_id = connection_pool.execute_query(
                query_movimento, 
                (sessao_id, valor, motivo, usuario_id, pdv_id, forma_pagamento_id)
            )
            
            # Inserir detalhe
            query_detalhe = """
            INSERT INTO sangria_detalhe 
            (sangria_id, forma_pagamento_id, valor_sistema, valor_sangria, diferenca, observacao)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            connection_pool.execute_query(
                query_detalhe,
                (movimento_id, forma_pagamento_id, valor_sistema, valor, diferenca, motivo)
            )
            
            # Atualizar sessão
            self._atualizar_total_sangrias(sessao_id)
            
            self.logger.info(f"Sangria registrada: {valor} Kz, Forma: {forma_pagamento_id}")
            return True, movimento_id
            
        except Exception as e:
            self.logger.error(f"Erro ao registrar sangria: {e}")
            return False, 0
    
    def registrar_suprimento(self, sessao_id: int, pdv_id: int, usuario_id: int,
                            forma_pagamento_id: int, valor: float, motivo: str = "") -> bool:
        """Registrar suprimento no sistema"""
        try:
            # Inserir movimento principal
            query_movimento = """
            INSERT INTO caixa_movimentos 
            (sessao_id, tipo, valor, motivo, usuario_id, pdv_id, forma_pagamento_id)
            VALUES (%s, 'REFORCO', %s, %s, %s, %s, %s)
            """
            
            movimento_id = connection_pool.execute_query(
                query_movimento, 
                (sessao_id, valor, motivo, usuario_id, pdv_id, forma_pagamento_id)
            )
            
            # Inserir detalhe
            query_detalhe = """
            INSERT INTO suprimento_detalhe 
            (suprimento_id, forma_pagamento_id, valor, observacao)
            VALUES (%s, %s, %s, %s)
            """
            
            connection_pool.execute_query(
                query_detalhe,
                (movimento_id, forma_pagamento_id, valor, motivo)
            )
            
            # Atualizar sessão
            self._atualizar_total_reforcos(sessao_id)
            
            self.logger.info(f"Suprimento registrado: {valor} Kz, Forma: {forma_pagamento_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao registrar suprimento: {e}")
            return False
    
    def _get_valor_sistema_forma(self, sessao_id: int, forma_pagamento_id: int) -> float:
        """Obter valor em sistema por forma de pagamento"""
        try:
            # Esta é uma função auxiliar - precisa ser implementada
            # ou substituída por uma query real
            query = """
            SELECT COALESCE(SUM(total_pago), 0) as valor
            FROM vendas v
            WHERE v.forma_pagamento_id = %s
                AND EXISTS (
                    SELECT 1 FROM caixa_sessao cs 
                    WHERE cs.id = %s 
                    AND v.data_emissao >= cs.data_abertura
                    AND (cs.data_fecho IS NULL OR v.data_emissao <= cs.data_fecho)
                )
            """
            
            result = connection_pool.execute_query(
                query, (forma_pagamento_id, sessao_id), fetchone=True
            )
            
            return float(result['valor']) if result else 0.0
            
        except Exception as e:
            self.logger.error(f"Erro ao obter valor sistema: {e}")
            return 0.0
    
    def _atualizar_total_sangrias(self, sessao_id: int):
        """Atualizar total de sangrias na sessão"""
        try:
            query = """
            UPDATE caixa_sessao 
            SET total_sangrias = (
                SELECT COALESCE(SUM(valor), 0) 
                FROM caixa_movimentos 
                WHERE sessao_id = %s AND tipo = 'SANGRIA'
            )
            WHERE id = %s
            """
            
            connection_pool.execute_query(query, (sessao_id, sessao_id))
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar sangrias: {e}")
    
    def _atualizar_total_reforcos(self, sessao_id: int):
        """Atualizar total de reforços na sessão"""
        try:
            query = """
            UPDATE caixa_sessao 
            SET total_reforcos = (
                SELECT COALESCE(SUM(valor), 0) 
                FROM caixa_movimentos 
                WHERE sessao_id = %s AND tipo = 'REFORCO'
            )
            WHERE id = %s
            """
            
            connection_pool.execute_query(query, (sessao_id, sessao_id))
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar reforcos: {e}")
    
    def get_resumo_sangrias(self, sessao_id: int) -> Dict[str, Any]:
        """Obter resumo de sangrias da sessão"""
        try:
            query = """
            SELECT 
                fp.nome,
                fp.codigo,
                COUNT(DISTINCT cm.id) as total_sangrias,
                SUM(cm.valor) as valor_total,
                AVG(sd.diferenca) as diferenca_media,
                MIN(sd.diferenca) as diferenca_min,
                MAX(sd.diferenca) as diferenca_max
            FROM caixa_movimentos cm
            JOIN forma_pagamento fp ON cm.forma_pagamento_id = fp.id
            LEFT JOIN sangria_detalhe sd ON cm.id = sd.sangria_id
            WHERE cm.sessao_id = %s AND cm.tipo = 'SANGRIA'
            GROUP BY fp.id, fp.nome, fp.codigo
            """
            
            resumo = connection_pool.execute_query(query, (sessao_id,), fetchall=True)
            
            # Calcular totais
            total_sangrias = sum(item['valor_total'] for item in resumo)
            total_diferenca = sum(item.get('diferenca_media', 0) * item.get('total_sangrias', 0) 
                                for item in resumo)
            
            return {
                'detalhes': resumo,
                'total_sangrias': total_sangrias,
                'total_diferenca': total_diferenca,
                'formas_com_sangria': len(resumo)
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter resumo: {e}")
            return {}

# Instância global
caixa_manager = CaixaManager()