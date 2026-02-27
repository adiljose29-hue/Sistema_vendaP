# database.py
import mysql.connector
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime
from connection_manager import connection_pool

class DatabaseManager:
    """Gerenciador avançado de operações de banco de dados"""
    
    def __init__(self, connection_manager=None):
        self.connection_manager = connection_manager or connection_pool
        self.logger = logging.getLogger('DatabaseManager')
    
    def get_product_by_code(self, product_code: str) -> Optional[Dict[str, Any]]:
        """Obter produto por código"""
        try:
            query = """
            SELECT p.*, t.percentagem as taxa_percentagem, t.codigo as taxa_codigo
            FROM produtos p
            LEFT JOIN taxa t ON p.taxa_id = t.id
            WHERE p.codigo = %s AND p.ativo = 1
            """
            
            result = self.connection_manager.execute_query(
                query, (product_code,), fetchone=True
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar produto {product_code}: {e}")
            return None
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Obter produto por ID"""
        try:
            query = """
            SELECT p.*, t.percentagem as taxa_percentagem, t.codigo as taxa_codigo
            FROM produtos p
            LEFT JOIN taxa t ON p.taxa_id = t.id
            WHERE p.id = %s AND p.ativo = 1
            """
            
            result = self.connection_manager.execute_query(
                query, (product_id,), fetchone=True
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar produto ID {product_id}: {e}")
            return None
    
    def get_active_taxes(self) -> List[Dict[str, Any]]:
        """Obter todas as taxas ativas"""
        try:
            query = """
            SELECT * FROM taxa WHERE ativo = 1 ORDER BY percentagem
            """
            
            result = self.connection_manager.execute_query(query, fetchall=True)
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar taxas: {e}")
            return []
    
    def get_payment_methods(self, loja_id: int = None) -> List[Dict[str, Any]]:
        """Obter métodos de pagamento"""
        try:
            if loja_id:
                query = """
                SELECT * FROM forma_pagamento 
                WHERE (loja_id = %s OR loja_id IS NULL) AND ativo = 1
                ORDER BY nome
                """
                params = (loja_id,)
            else:
                query = "SELECT * FROM forma_pagamento WHERE ativo = 1 ORDER BY nome"
                params = None
            
            result = self.connection_manager.execute_query(query, params, fetchall=True)
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar métodos de pagamento: {e}")
            return []
    
    def get_client_by_nif(self, nif: str) -> Optional[Dict[str, Any]]:
        """Obter cliente por NIF"""
        try:
            query = """
            SELECT * FROM clientes 
            WHERE nif = %s AND ativo = 1
            """
            
            result = self.connection_manager.execute_query(
                query, (nif,), fetchone=True
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar cliente NIF {nif}: {e}")
            return None
    
    def get_client_by_id(self, client_id: int) -> Optional[Dict[str, Any]]:
        """Obter cliente por ID"""
        try:
            query = """
            SELECT * FROM clientes 
            WHERE id = %s AND ativo = 1
            """
            
            result = self.connection_manager.execute_query(
                query, (client_id,), fetchone=True
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar cliente ID {client_id}: {e}")
            return None
    
    def get_next_document_number(self, loja_id: int, pdv_id: int, 
                                tipo_venda: str, ano: int) -> int:
        """Obter próximo número de documento"""
        try:
            # Verificar se já existe sequência para este ano
            query_check = """
            SELECT ultimo_numero FROM sequencias_vendas
            WHERE loja_id = %s AND pdv_id = %s AND tipo_venda = %s AND ano = %s
            """
            
            result = self.connection_manager.execute_query(
                query_check, (loja_id, pdv_id, tipo_venda, ano), fetchone=True
            )
            
            if result:
                next_number = result['ultimo_numero'] + 1
                
                # Atualizar sequência
                query_update = """
                UPDATE sequencias_vendas 
                SET ultimo_numero = %s, data_ultima_emissao = NOW()
                WHERE loja_id = %s AND pdv_id = %s AND tipo_venda = %s AND ano = %s
                """
                
                self.connection_manager.execute_query(
                    query_update, (next_number, loja_id, pdv_id, tipo_venda, ano)
                )
                
                return next_number
            else:
                # Criar nova sequência
                next_number = 1
                
                query_insert = """
                INSERT INTO sequencias_vendas 
                (loja_id, pdv_id, tipo_venda, ano, ultimo_numero, data_ultima_emissao)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """
                
                self.connection_manager.execute_query(
                    query_insert, (loja_id, pdv_id, tipo_venda, ano, next_number)
                )
                
                return next_number
                
        except Exception as e:
            self.logger.error(f"Erro ao obter próximo número de documento: {e}")
            return 1
    
    # database.py - Modificar create_sale() para preencher pagamentos

    def create_sale(self, sale_data: Dict[str, Any]) -> Tuple[bool, Optional[int], str]:
        """Criar nova venda no banco de dados - VERSÃO CORRIGIDA"""
        try:
            # Iniciar transação
            connection = self.connection_manager.get_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Obter próximo número
            doc_number = self.get_next_document_number(
                sale_data['loja_id'],
                sale_data['pdv_id'],
                sale_data['tipo'],
                sale_data['ano']
            )
            
            # Formatar número do documento
            if sale_data['tipo'] in ['FS', 'NC', 'ND']:
                numero_documento = f"{sale_data['tipo']}/{sale_data['ano']}/{sale_data['loja_id']:04d}/{sale_data['pdv_id']:03d}/{doc_number:06d}"
            else:
                numero_documento = f"{sale_data['tipo']}/{sale_data['ano']}/{doc_number:06d}"
            
            # OBTER forma_pagamento_id do banco (não do mapa estático)
            forma_pagamento_nome = sale_data.get('forma_pagamento', 'DINHEIRO')
            
            # Buscar ID da forma de pagamento no banco
            query_forma = "SELECT id FROM forma_pagamento WHERE codigo = %s OR nome LIKE %s LIMIT 1"
            
            # Mapear nomes para códigos
            forma_map = {
                'DINHEIRO': 'DIN',
                'CARTÃO DÉBITO': 'MC',
                'CARTÃO CRÉDITO': 'CC', 
                'TPA MÓVEL': 'TPA',
                'CARTÃO CLIENTE': 'CL'
            }
            
            codigo_forma = forma_map.get(forma_pagamento_nome.upper(), 'DIN')
            busca_nome = f"%{forma_pagamento_nome}%"
            
            result_forma = cursor.execute(query_forma, (codigo_forma, busca_nome))
            result_forma = cursor.fetchone()
            
            if result_forma:
                forma_pagamento_id = result_forma['id']
            else:
                # Usar dinheiro como padrão
                forma_pagamento_id = 1
            
            # **CRÍTICO: Obter sessão atual do caixa**
            sessao_id = None
            if 'sessao_id' in sale_data:
                # Tentar obter ID da sessão do caixa
                query_sessao = """
                SELECT id FROM caixa_sessao 
                WHERE pdv_id = %s AND estado = 'ABERTA' 
                ORDER BY data_abertura DESC LIMIT 1
                """
                cursor.execute(query_sessao, (sale_data['pdv_id'],))
                sessao_result = cursor.fetchone()
                if sessao_result:
                    sessao_id = sessao_result['id']
            
            # **CORREÇÃO: Usar data_emissao corretamente**
            data_emissao = sale_data.get('data_emissao')
            system_entry_date = sale_data.get('system_entry_date', data_emissao)
            
            # Se data_emissao for string, converter para datetime
            if isinstance(data_emissao, str):
                from datetime import datetime
                try:
                    # Tentar converter formato MySQL
                    data_emissao = datetime.strptime(data_emissao, '%Y-%m-%d %H:%M:%S')
                    system_entry_date = datetime.strptime(system_entry_date, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    # Tentar formato brasileiro
                    try:
                        data_emissao = datetime.strptime(data_emissao, '%d/%m/%Y %H:%M')
                        system_entry_date = datetime.strptime(system_entry_date, '%d/%m/%Y %H:%M')
                    except ValueError:
                        # Usar agora
                        data_emissao = datetime.now()
                        system_entry_date = datetime.now()
            
            # Inserir venda
            query_venda = """
            INSERT INTO vendas (
                empresa_id, loja_id, pdv_id, usuario_id, cliente_id,
                numero_venda, tipo, numero_documento, taxa_id,
                valor_iva, total_sem_iva, total_iva, total_com_iva,
                estado, forma_pagamento_id, total_venda, total_pago, troco,
                data_emissao, system_entry_date, source_id,
                desconto_global, total_desconto, created_at
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, NOW()
            )
            """
            
            cursor.execute(query_venda, (
                sale_data['empresa_id'], sale_data['loja_id'], sale_data['pdv_id'],
                sale_data['usuario_id'], sale_data.get('cliente_id', 1),
                sale_data['numero_venda'], sale_data['tipo'], numero_documento,
                sale_data.get('taxa_id', 1),
                sale_data.get('valor_iva', 0), sale_data.get('total_sem_iva', sale_data['total_venda']),
                sale_data.get('total_iva', 0), sale_data.get('total_com_iva', sale_data['total_venda']),
                'EMITIDO', forma_pagamento_id,
                sale_data['total_venda'], sale_data['total_pago'],
                sale_data.get('troco', 0),
                data_emissao, system_entry_date,
                sale_data.get('source_id', sale_data['usuario_id']),
                sale_data.get('desconto_global', 0), sale_data.get('total_desconto', 0)
            ))
            
            venda_id = cursor.lastrowid
            
            # **CRÍTICO: Registrar pagamento na tabela pagamentos**
            query_pagamento = """
            INSERT INTO pagamentos (
                venda_id, metodo, total_venda, total_pago, troco,
                sessao_id, pdv_id, usuario_id, forma_pagamento_id,
                estado, data_pagamento
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            )
            """
            
            cursor.execute(query_pagamento, (
                venda_id, 
                forma_pagamento_nome.upper(),  # método
                sale_data['total_venda'],
                sale_data['total_pago'],
                sale_data.get('troco', 0),
                sessao_id,  # Pode ser NULL
                sale_data['pdv_id'],
                sale_data['usuario_id'],
                forma_pagamento_id,
                'CONCLUIDO',
                data_emissao  # Usar mesma data da venda
            ))
            
            # Inserir itens da venda
            for item in sale_data['itens']:
                query_item = """
                INSERT INTO venda_itens (
                    venda_id, produto_id, descricao, quantidade,
                    preco_unitario, total, taxa_iva,
                    preco_original, desconto_percentual, desconto_valor,
                    total_desconto, total_liquido, created_at
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, NOW()
                )
                """
                
                cursor.execute(query_item, (
                    venda_id, item['produto_id'], item['descricao'],
                    item['quantidade'], item['preco_unitario'], item['total'],
                    item.get('taxa_iva', item.get('taxa_percentagem', 0)),
                    item.get('preco_original', item['preco_unitario']),
                    item.get('desconto_percentual', 0), item.get('desconto_valor', 0),
                    item.get('total_desconto', 0), item.get('total_liquido', item['total'])
                ))
                
                # Atualizar estoque
                if item.get('atualizar_estoque', True):
                    query_estoque = """
                    UPDATE produtos 
                    SET stock_atual = stock_atual - %s,
                        stock_reservado = stock_reservado - %s
                    WHERE id = %s
                    """
                    
                    cursor.execute(query_estoque, (
                        item['quantidade'], item['quantidade'], item['produto_id']
                    ))
            
            # Commit da transação
            connection.commit()
            
            self.logger.info(f"Venda {venda_id} criada com sucesso. Documento: {numero_documento}")
            self.logger.info(f"Pagamento registrado para venda {venda_id}, Forma: {forma_pagamento_id}")
            
            return True, venda_id, numero_documento
            
        except Exception as e:
            self.logger.error(f"Erro ao criar venda: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            if 'connection' in locals():
                connection.rollback()
            return False, None, str(e)
            
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'connection' in locals():
                self.connection_manager.return_connection(connection)
        
    def get_daily_sales_summary(self, loja_id: int, data: datetime) -> Dict[str, Any]:
        """Obter resumo de vendas do dia"""
        try:
            query = """
            SELECT 
                COUNT(*) as total_vendas,
                SUM(total_venda) as total_valor,
                SUM(total_iva) as total_iva,
                COUNT(DISTINCT cliente_id) as total_clientes
            FROM vendas
            WHERE loja_id = %s 
                AND DATE(data_emissao) = DATE(%s)
                AND estado = 'EMITIDO'
            """
            
            result = self.connection_manager.execute_query(
                query, (loja_id, data), fetchone=True
            )
            
            return result or {}
            
        except Exception as e:
            self.logger.error(f"Erro ao obter resumo de vendas: {e}")
            return {}
    
    def check_stock(self, produto_id: int, quantidade: float, loja_id: int = None) -> bool:
        """Verificar se há estoque disponível"""
        try:
            if loja_id:
                query = """
                SELECT stock_atual - stock_reservado as disponivel
                FROM produtos 
                WHERE id = %s AND loja_id = %s
                """
                params = (produto_id, loja_id)
            else:
                query = """
                SELECT stock_atual - stock_reservado as disponivel
                FROM produtos 
                WHERE id = %s
                """
                params = (produto_id,)
            
            result = self.connection_manager.execute_query(query, params, fetchone=True)
            
            if result and result['disponivel'] >= quantidade:
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao verificar estoque: {e}")
            return False

    def get_active_payment_methods(self, loja_id: int = None) -> List[Dict[str, Any]]:
        """Obter métodos de pagamento ativos"""
        try:
            if loja_id:
                query = """
                SELECT * FROM forma_pagamento 
                WHERE (loja_id = %s OR loja_id IS NULL) 
                  AND ativo = 1 
                ORDER BY nome
                """
                params = (loja_id,)
            else:
                query = """
                SELECT * FROM forma_pagamento 
                WHERE ativo = 1 
                ORDER BY nome
                """
                params = None
            
            result = self.connection_manager.execute_query(query, params, fetchall=True)
            return result
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar métodos de pagamento: {e}")
            # Retornar métodos padrão
            return [
                {'id': 1, 'nome': 'DINHEIRO', 'codigo': 'DIN', 'aceita_troco': 1},
                {'id': 2, 'nome': 'CARTÃO DÉBITO', 'codigo': 'DEB', 'aceita_troco': 0},
                {'id': 3, 'nome': 'CARTÃO CRÉDITO', 'codigo': 'CRE', 'aceita_troco': 0},
                {'id': 4, 'nome': 'TPA MÓVEL', 'codigo': 'TPA', 'aceita_troco': 0},
                {'id': 5, 'nome': 'CARTÃO CLIENTE', 'codigo': 'CCL', 'aceita_troco': 0}
            ]
    

# Instância global para uso rápido
db = DatabaseManager()