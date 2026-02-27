# promotion_manager.py
import json
from datetime import datetime, time
from typing import Dict, List, Any, Optional, Tuple
import logging
from config_manager import config
from connection_manager import connection_pool

class PromotionManager:
    """Gerenciador de promoções e descontos"""
    
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
        self.active_promotions = {}
        self.logger = logging.getLogger('PromotionManager')
        self._setup_logging()
        self._load_active_promotions()
    
    def _setup_logging(self):
        """Configurar logging"""
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/promotions.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _load_active_promotions(self):
        """Carregar promoções ativas do banco"""
        try:
            query = """
            SELECT p.*, tp.nome as tipo_nome
            FROM promocoes p
            JOIN tipos_promocao tp ON p.tipo_promocao_id = tp.id
            WHERE p.ativo = 1 
                AND CURDATE() BETWEEN p.data_inicio AND p.data_fim
                AND CURTIME() BETWEEN p.hora_inicio AND p.hora_fim
            """
            
            promotions = connection_pool.execute_query(query, fetchall=True)
            
            for promo in promotions:
                promo_id = promo['id']
                self.active_promotions[promo_id] = promo
                
                # Carregar detalhes específicos
                if promo['tipo_promocao_id'] == 1:  # Desconto Percentual
                    self._load_percentual_details(promo_id)
                elif promo['tipo_promocao_id'] == 3:  # Compre X Leve Y
                    self._load_compre_x_details(promo_id)
                elif promo['tipo_promocao_id'] == 4:  # Combo
                    self._load_combo_details(promo_id)
                elif promo['tipo_promocao_id'] == 5:  # Desconto Progressivo
                    self._load_progressivo_details(promo_id)
            
            self.logger.info(f"Carregadas {len(promotions)} promoções ativas")
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar promoções: {e}")
    
    def _load_percentual_details(self, promo_id: int):
        """Carregar detalhes de desconto percentual"""
        try:
            query = """
            SELECT pp.*, pr.codigo as produto_codigo, pr.descricao
            FROM promocao_produtos pp
            JOIN produtos pr ON pp.produto_id = pr.id
            WHERE pp.promocao_id = %s
            """
            
            produtos = connection_pool.execute_query(query, (promo_id,), fetchall=True)
            self.active_promotions[promo_id]['produtos'] = produtos
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar produtos promoção {promo_id}: {e}")
    
    def check_promotions_for_product(self, product_id: int, quantidade: float, 
                                   cliente_id: int = None, total_venda: float = 0) -> List[Dict]:
        """Verificar promoções aplicáveis a um produto"""
        aplicaveis = []
        
        for promo_id, promo in self.active_promotions.items():
            if self._is_promotion_applicable(promo, product_id, cliente_id, total_venda):
                desconto = self._calculate_discount(promo, product_id, quantidade, total_venda)
                if desconto:
                    aplicaveis.append({
                        'promocao_id': promo_id,
                        'nome': promo['nome'],
                        'tipo': promo['tipo_nome'],
                        'desconto': desconto
                    })
        
        return aplicaveis
    
    def _is_promotion_applicable(self, promo: Dict, product_id: int, 
                                cliente_id: int = None, total_venda: float = 0) -> bool:
        """Verificar se promoção é aplicável"""
        try:
            aplicavel_em = promo.get('aplicavel_em', 'PRODUTO')
            
            if aplicavel_em == 'PRODUTO':
                # Verificar se produto está na promoção
                query = "SELECT 1 FROM promocao_produtos WHERE promocao_id = %s AND produto_id = %s"
                result = connection_pool.execute_query(query, (promo['id'], product_id), fetchone=True)
                return result is not None
            
            elif aplicavel_em == 'CLIENTE':
                if not cliente_id:
                    return False
                query = "SELECT 1 FROM promocao_clientes WHERE promocao_id = %s AND cliente_id = %s"
                result = connection_pool.execute_query(query, (promo['id'], cliente_id), fetchone=True)
                return result is not None
            
            elif aplicavel_em == 'CATEGORIA':
                # Verificar categoria do produto
                query = """
                SELECT 1 FROM promocao_categorias pc
                JOIN produtos p ON p.categoria_id = pc.categoria_id
                WHERE pc.promocao_id = %s AND p.id = %s
                """
                result = connection_pool.execute_query(query, (promo['id'], product_id), fetchone=True)
                return result is not None
            
            return False
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar promoção: {e}")
            return False
    
    def _calculate_discount(self, promo: Dict, product_id: int, 
                          quantidade: float, total_venda: float) -> Optional[Dict]:
        """Calcular desconto da promoção"""
        try:
            tipo = promo['tipo_promocao_id']
            
            if tipo == 1:  # Desconto Percentual
                if promo.get('percentual'):
                    return {
                        'tipo': 'percentual',
                        'valor': float(promo['percentual']),
                        'descricao': f"{promo['percentual']}% desconto"
                    }
            
            elif tipo == 2:  # Desconto Fixo
                if promo.get('valor_fixo'):
                    return {
                        'tipo': 'fixo',
                        'valor': float(promo['valor_fixo']),
                        'descricao': f"{promo['valor_fixo']} Kz desconto"
                    }
            
            elif tipo == 3:  # Compre X Leve Y
                quantidade_minima = self._get_minimum_quantity(promo['id'], product_id)
                if quantidade_minima and quantidade >= quantidade_minima:
                    # Para cada X unidades, dar Y grátis
                    gratis = promo.get('leva_gratis_qtd', 1)
                    return {
                        'tipo': 'compre_x',
                        'quantidade_minima': quantidade_minima,
                        'gratis': gratis,
                        'descricao': f"Compre {quantidade_minima} leve {gratis} grátis"
                    }
            
            elif tipo == 5:  # Desconto Progressivo
                if total_venda >= float(promo.get('compra_minima', 0)):
                    query = """
                    SELECT desconto_percentual 
                    FROM desconto_progressivo 
                    WHERE promocao_id = %s 
                        AND valor_minimo <= %s 
                        AND (valor_maximo IS NULL OR valor_maximo > %s)
                    ORDER BY valor_minimo DESC LIMIT 1
                    """
                    result = connection_pool.execute_query(query, 
                        (promo['id'], total_venda, total_venda), fetchone=True)
                    
                    if result:
                        return {
                            'tipo': 'progressivo',
                            'valor': float(result['desconto_percentual']),
                            'descricao': f"Desconto progressivo: {result['desconto_percentual']}%"
                        }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao calcular desconto: {e}")
            return None
    
    def _get_minimum_quantity(self, promo_id: int, product_id: int) -> Optional[float]:
        """Obter quantidade mínima para promoção"""
        try:
            query = """
            SELECT quantidade_minima 
            FROM promocao_produtos 
            WHERE promocao_id = %s AND produto_id = %s
            """
            result = connection_pool.execute_query(query, (promo_id, product_id), fetchone=True)
            return float(result['quantidade_minima']) if result else None
        except:
            return None
    
    def apply_promotion_to_sale(self, venda_id: int, promocao_id: int, 
                               desconto_info: Dict, produto_id: int = None, 
                               cliente_id: int = None):
        """Registrar promoção aplicada na venda"""
        try:
            query = """
            INSERT INTO promocao_aplicada 
            (venda_id, promocao_id, produto_id, cliente_id, 
             valor_desconto, percentual_desconto)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            valor_desconto = desconto_info.get('valor', 0)
            percentual = desconto_info.get('valor') if desconto_info.get('tipo') == 'percentual' else None
            
            connection_pool.execute_query(query, (
                venda_id, promocao_id, produto_id, cliente_id,
                valor_desconto, percentual
            ))
            
            self.logger.info(f"Promoção {promocao_id} aplicada à venda {venda_id}")
            
        except Exception as e:
            self.logger.error(f"Erro ao registrar promoção: {e}")

# Instância global
promotion_manager = PromotionManager()