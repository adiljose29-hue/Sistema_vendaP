# document_manager.py 
from datetime import datetime
from typing import Dict, Any, Optional, Tuple  # ADICIONAR Tuple
import logging
from config_manager import config
from connection_manager import connection_pool

class DocumentManager:
    """Gerenciador de numeração e seleção de documentos fiscais"""
    
    def __init__(self):
        self.logger = logging.getLogger('DocumentManager')
        self._setup_logging()
    
    def _setup_logging(self):
        """Configurar sistema de logs"""
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/documents.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def get_document_type(self, total_venda: float, cliente_nif: str = None) -> Tuple[str, str]:
        """
        Determinar tipo de documento baseado no valor e cliente
        """
        # Obter limites do config
        limite_fs = config.getfloat('DOCUMENT', 'limit_factura_simplificada', 35000.00)
        limite_fr = config.getfloat('DOCUMENT', 'limit_factura_recibo', 100000.00)
        
        # Verificar se cliente tem NIF válido
        nif_valido = cliente_nif and cliente_nif != '0000000000' and len(cliente_nif) >= 9
        
        self.logger.info(f"Documento - Total: {total_venda}, NIF: {cliente_nif}, NIF válido: {nif_valido}")
        
        # DECISÃO SIMPLIFICADA PARA TESTE:
        # 1. Se valor <= 35.000: FS (sempre)
        # 2. Se valor <= 100.000: FR (se tiver NIF), senão FS
        # 3. Se valor > 100.000: FT (se tiver NIF), senão pedir para usar consumidor final
        
        if total_venda <= limite_fs:
            return 'FS', 'Factura Simplificada'
        
        elif total_venda <= limite_fr:
            if nif_valido:
                return 'FR', 'Factura-Recibo'
            else:
                # Sem NIF válido, usar FS mesmo acima do limite
                self.logger.warning(f"Cliente sem NIF para FR, usando FS")
                return 'FS', 'Factura Simplificada'
        
        else:
            # Valor alto (> 100.000)
            if nif_valido:
                return 'FT', 'Factura'
            else:
                # Não pode emitir FT sem NIF
                raise ValueError(f"Valor {total_venda:.2f} Kz requer NIF para Factura")
        
    def generate_document_info(self, loja_id: int, pdv_id: int, 
                             total_venda: float, cliente_nif: str = None) -> Dict[str, Any]:
        """
        Gerar informações completas do documento
        
        Retorna: {
            'tipo': 'FS'/'FR'/'FT',
            'descricao': 'Factura Simplificada',
            'numero_venda': '2025000100100123',
            'numero_documento': 'FS 0001001/000123/2025',
            'requires_nif': True/False,
            'copies': 1/2
        }
        """
        try:
            # Determinar tipo de documento
            tipo, descricao = self.get_document_type(total_venda, cliente_nif)
            
            # Obter sequência
            ano = datetime.now().year
            seq_info = self.get_next_sequence(loja_id, pdv_id, tipo, ano)
            
            # Determinar número de cópias
            copies_config = {
                'FS': config.getint('DOCUMENT', 'copies_factura_simplificada', 1),
                'FR': config.getint('DOCUMENT', 'copies_factura_recibo', 2),
                'FT': config.getint('DOCUMENT', 'copies_factura', 2)
            }
            
            copies = copies_config.get(tipo, 1)
            
            return {
                'tipo': tipo,
                'descricao': descricao,
                'numero_venda': seq_info['numero_venda'],
                'numero_documento': seq_info['numero_documento'],
                'requires_nif': cliente_nif and cliente_nif != '0000000000',
                'copies': copies,
                'sequencia': seq_info['sequencia'],
                'ano': ano
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao gerar documento: {e}")
            # Fallback: FS
            ano = datetime.now().year
            seq_info = self.get_next_sequence(loja_id, pdv_id, 'FS', ano)
            
            return {
                'tipo': 'FS',
                'descricao': 'Factura Simplificada',
                'numero_venda': seq_info['numero_venda'],
                'numero_documento': seq_info['numero_documento'],
                'requires_nif': False,
                'copies': 1,
                'sequencia': seq_info['sequencia'],
                'ano': ano
            }
    
    def generate_internal_number(self, loja_id: int, pdv_id: int, sequencia: int) -> str:
        """
        Gerar número interno da venda: AAAALLLLPPPTTTTTT
        
        AAAA - Ano (4 dígitos)
        LLLL - Loja (4 dígitos)
        PPP - PDV (3 dígitos)
        TTTTTT - Sequência (6 dígitos)
        
        Exemplo: 2025000100100123
        """
        ano = datetime.now().year
        dia = datetime.now().day
        return f"{dia:02d}{ano:04d}{loja_id:04d}{pdv_id:03d}{sequencia:06d}"
    
    def generate_document_number(self, tipo: str, loja_id: int, pdv_id: int, 
                                sequencia: int, ano: int = None) -> str:
        """
        Gerar número do documento fiscal: FF LLLLPPP/TTTTTT/AAAA
        
        FF - Tipo (2 caracteres)
        LLLL - Loja (4 dígitos)
        PPP - PDV (3 dígitos) - opcional para alguns tipos
        TTTTTT - Sequência (6 dígitos)
        AAAA - Ano (4 dígitos)
        
        Exemplos:
        FT 0001001/000123/2025
        FS 0001001/000123/2025
        """
        if ano is None:
            ano = datetime.now().year
        
        # Format based on document type
        if tipo in ['FS', 'NC', 'ND']:  # Factura Simplificada, Notas
            # Inclui PDV: LLLLPPP
            return f"{tipo} {loja_id:04d}{pdv_id:03d}/{sequencia:06d}/{ano:04d}"
        else:  # FT, FR
            # Sem PDV: LLLL
            return f"{tipo} {loja_id:04d}{pdv_id:03d}/{sequencia:06d}/{ano:04d}"
            #return f"{tipo} {loja_id:04d}/{sequencia:06d}/{ano:04d}"
    
    def get_next_sequence(self, loja_id: int, pdv_id: int, 
                         tipo_venda: str, ano: int = None) -> Dict[str, Any]:
        """
        Obter próxima sequência para venda
        
        Retorna: {
            'sequencia': int,
            'numero_venda': str,
            'numero_documento': str
        }
        """
        if ano is None:
            ano = datetime.now().year
        
        try:
            # Obter sequência do banco
            query = """
            SELECT ultimo_numero FROM sequencias_vendas
            WHERE loja_id = %s AND pdv_id = %s AND tipo_venda = %s AND ano = %s
            """
            
            result = connection_pool.execute_query(
                query, (loja_id, pdv_id, tipo_venda, ano), fetchone=True
            )
            
            if result:
                sequencia = result['ultimo_numero'] + 1
                
                # Atualizar sequência
                update_query = """
                UPDATE sequencias_vendas 
                SET ultimo_numero = %s, data_ultima_emissao = NOW()
                WHERE loja_id = %s AND pdv_id = %s AND tipo_venda = %s AND ano = %s
                """
                
                connection_pool.execute_query(
                    update_query, (sequencia, loja_id, pdv_id, tipo_venda, ano)
                )
            else:
                # Criar nova sequência
                sequencia = 1
                insert_query = """
                INSERT INTO sequencias_vendas 
                (loja_id, pdv_id, tipo_venda, ano, ultimo_numero, data_ultima_emissao)
                VALUES (%s, %s, %s, %s, %s, NOW())
                """
                
                connection_pool.execute_query(
                    insert_query, (loja_id, pdv_id, tipo_venda, ano, sequencia)
                )
            
            # Gerar números
            numero_venda = self.generate_internal_number(loja_id, pdv_id, sequencia)
            numero_documento = self.generate_document_number(
                tipo_venda, loja_id, pdv_id, sequencia, ano
            )
            
            self.logger.info(
                f"Sequência gerada - Tipo: {tipo_venda}, "
                f"Loja: {loja_id}, PDV: {pdv_id}, "
                f"Sequência: {sequencia}"
            )
            
            return {
                'sequencia': sequencia,
                'numero_venda': numero_venda,
                'numero_documento': numero_documento,
                'ano': ano
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter sequência: {e}")
            # Fallback: usar timestamp como sequência
            sequencia_fallback = int(datetime.now().timestamp() % 1000000)
            return {
                'sequencia': sequencia_fallback,
                'numero_venda': self.generate_internal_number(
                    loja_id, pdv_id, sequencia_fallback
                ),
                'numero_documento': self.generate_document_number(
                    tipo_venda, loja_id, pdv_id, sequencia_fallback, ano
                ),
                'ano': ano
            }
    
    def validate_document_number(self, numero_documento: str) -> bool:
        """
        Validar formato do número do documento
        """
        # Implementar lógica de validação conforme normas AGT
        # Por enquanto, validação básica
        if not numero_documento or len(numero_documento) < 10:
            return False
        
        parts = numero_documento.split()
        if len(parts) != 2:
            return False
        
        tipo = parts[0]
        if tipo not in ['FT', 'FR', 'FS', 'NC', 'ND']:
            return False
        
        return True

# Instância global
document_manager = DocumentManager()