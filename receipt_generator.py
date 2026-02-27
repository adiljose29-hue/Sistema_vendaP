# receipt_generator.py 
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from config_manager import config

class ReceiptGenerator:
    """Gerador de recibos fiscais com resumo IVA - VERSÃO CORRIGIDA"""
    
    def __init__(self):
        self.logger = logging.getLogger('ReceiptGenerator')
        self._setup_logging()
    
    def _setup_logging(self):
        """Configurar sistema de logs"""
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/receipts.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
        # receipt_generator.py - Corrigir o método formatar_moeda
    
    def formatar_moeda(self, valor, show_symbol: bool = True) -> str:
        """Formatar valor como moeda - CORRIGIDO"""
        try:
            # Converter para float se necessário
            if isinstance(valor, str):
                valor = float(valor.replace(',', '.'))
            
            # Se é Decimal, converter para float
            if hasattr(valor, 'to_eng_string'):
                valor = float(valor)
            
            # Obter configurações - CORRIGIDO: usar apenas 3 argumentos
            dec_sep = config.get('CURRENCY', 'decimal_separator', ',')  # CORRIGIDO
            thou_sep = config.get('CURRENCY', 'thousands_separator', '.')  # CORRIGIDO
            symbol = config.get('CURRENCY', 'symbol', 'Kz')  # CORRIGIDO
            
            # Formatar número
            formatted = f"{valor:,.2f}"
            
            # Substituir separadores
            if dec_sep != '.':
                formatted = formatted.replace('.', 'X').replace(',', thou_sep).replace('X', dec_sep)
            elif thou_sep != ',':
                formatted = formatted.replace(',', 'X').replace('.', dec_sep).replace('X', thou_sep)
            
            # Adicionar símbolo
            if show_symbol:
                return f"{symbol} {formatted}"
            else:
                return formatted
            
        except Exception as e:
            self.logger.error(f"Erro ao formatar moeda {valor}: {e}")
            # Fallback simples
            return f"Kz {valor:,.2f}"
    
    def calculate_iva_summary(self, items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Calcular resumo de IVA - CORRIGIDO"""
        summary = {}
        
        for item in items:
            tax_rate = item.get('taxa_percentagem', 0)
            total = item.get('total', 0)
            
            # Determinar código da taxa
            tax_code = self._get_tax_code(tax_rate)
            
            # Calcular valores
            if tax_rate > 0:
                base_sem_iva = total / (1 + (tax_rate / 100))
                valor_iva = total - base_sem_iva
            else:
                base_sem_iva = total
                valor_iva = 0
            
            # Chave no formato correto
            tax_key = f"{tax_code} {tax_rate:.0f}%"
            
            if tax_key not in summary:
                summary[tax_key] = {
                    'tax_code': tax_code,
                    'tax_rate': tax_rate,
                    'base_sem_iva': 0.0,
                    'valor_iva': 0.0,
                    'total_com_iva': 0.0
                }
            
            summary[tax_key]['base_sem_iva'] += base_sem_iva
            summary[tax_key]['valor_iva'] += valor_iva
            summary[tax_key]['total_com_iva'] += total
        
        return summary
    
    def _get_tax_code(self, tax_percent: float) -> str:
        """Obter código da taxa"""
        if tax_percent == 7:
            return 'C'
        elif tax_percent == 14:
            return 'D'
        elif tax_percent == 12:
            return 'E'
        elif tax_percent == 0:
            return 'H'
        else:
            return '?'
    
    def generate_receipt_text(self, sale_data: Dict[str, Any]) -> str:
        """Gerar texto do recibo - CORRIGIDO"""
        lines = []
        
        # Configurações - CORRIGIDO sem fallback
        line_width = 48
        show_iva_summary = True
        
        try:
            line_width = int(config.get('RECEIPT', 'formatting_line_width', 'system', '48'))
            show_iva_summary = config.getboolean('RECEIPT', 'iva_summary_detailed', True)
        except:
            pass  # Usar valores padrão
        
        # Header
        lines.append("=" * line_width)
        lines.append("ESC MARKET".center(line_width))
        lines.append("=" * line_width)
        
        lines.append("ESC MARKET LDA".center(line_width))
        lines.append("Rua das Flores, 123".center(line_width))
        lines.append("Luanda - Angola".center(line_width))
        lines.append(f"NIF: 5000000000".center(line_width))
        lines.append(f"Tel: +244 923 456 789".center(line_width))
        
        lines.append("-" * line_width)
        
        # Informações da venda
        lines.append(f"{sale_data.get('document_description', 'FACTURA SIMPLIFICADA')}")
        lines.append(f"Documento: {sale_data.get('numero_documento', '')}")
        lines.append(f"Data: {sale_data.get('data_emissao', '')}")
        
        # Loja e caixa
        loja_id = sale_data.get('loja_id', 1)
        pdv_id = sale_data.get('pdv_id', 1)
        lines.append(f"Loja: {loja_id:04d}  Caixa: {pdv_id:03d}")
        
        lines.append(f"Cliente: {sale_data.get('cliente_nome', 'CONSUMIDOR FINAL')}")
        lines.append(f"NIF: {sale_data.get('cliente_nif', '0000000000')}")
        lines.append(f"Operador: {sale_data.get('operador_nome', '')}")
        
        lines.append("-" * line_width)
        
        # Itens
        lines.append(f"{'Código':<13} {'Descrição':<20} {'Qtd':>5} {'Preço':>8} {'Total':>10}")
        lines.append("-" * line_width)
        
        for item in sale_data.get('itens', []):
            codigo = str(item.get('codigo', ''))[:13]
            descricao = str(item.get('descricao', ''))[:20]
            quantidade = item.get('quantidade', 1)
            preco_unit = item.get('preco_unitario', 0)
            total = item.get('total', 0)
            taxa_percent = item.get('taxa_percentagem', 0)
            
            # Código da taxa
            tax_code = self._get_tax_code(taxa_percent)
            
            # Linha 1
            linha1 = f"{tax_code} {codigo:>12}  {descricao}"
            lines.append(linha1)
            
            # Linha 2
            qtd_str = f"{quantidade:.3f}".rstrip('0').rstrip('.')
            preco_str = self.formatar_moeda(preco_unit, False)
            total_str = self.formatar_moeda(total, False)
            
            linha2 = f"           {qtd_str:>5} X {preco_str:>8} = {total_str:>10}"
            lines.append(linha2)
        
        lines.append("-" * line_width)
        
        # Após os itens, adicionar:
        # Após os itens, adicionar seção de promoções
        if sale_data.get('promocoes_aplicadas'):
            lines.append("-" * line_width)
            lines.append("PROMOÇÕES APLICADAS:")
            total_desconto_promocao = 0
            
            for promocao in sale_data['promocoes_aplicadas']:
                if isinstance(promocao, dict):
                    nome = promocao.get('nome', 'Promoção')
                    valor = promocao.get('valor_desconto', 0)
                    produto = promocao.get('produto', '')
                    
                    if produto:
                        lines.append(f"  {nome} ({produto[:15]}...): -{self.formatar_moeda(valor, False)}")
                    else:
                        lines.append(f"  {nome}: -{self.formatar_moeda(valor, False)}")
                    
                    total_desconto_promocao += valor
            
            if total_desconto_promocao > 0:
                lines.append(f"{'Total descontos promoção:':<30} -{self.formatar_moeda(total_desconto_promocao):>18}")
            lines.append("-" * line_width)
        
        # ... resto do recibo ...
                
        # Totais
        total_geral = sale_data.get('total_venda', 0)
        total_pago = sale_data.get('total_pago', 0)
        troco = sale_data.get('troco', 0)
        
        lines.append(f"{'Total a pagar:':<30} {self.formatar_moeda(total_geral):>18}")
        lines.append(f"{'Valor pago:':<30} {self.formatar_moeda(total_pago):>18}")
        
        if troco > 0:
            lines.append(f"{'Troco:':<30} {self.formatar_moeda(troco):>18}")
        
        lines.append("-" * line_width)
        
        # Forma de pagamento
        lines.append(f"Forma de pagamento: {sale_data.get('forma_pagamento', 'DINHEIRO')}")
        
        # Resumo IVA - CORRIGIDO
        if show_iva_summary and sale_data.get('itens'):
            try:
                iva_summary = self.calculate_iva_summary(sale_data['itens'])
                
                if iva_summary:
                    lines.append(" ")
                    lines.append("RESUMO IVA IMPOSTO".center(line_width))
                    lines.append("-" * line_width)
                    
                    # Cabeçalho
                    header = f"{'Taxa':<6} {'Valor s/IVA':>12} {'Valor IVA':>12} {'Valor c/IVA':>12}"
                    lines.append(header)
                    lines.append("-" * line_width)
                    
                    # Ordenar por código da taxa - CORRIGIDO
                    tax_order = {'C': 1, 'D': 2, 'E': 3, 'H': 4}
                    
                    # Converter para lista ordenável
                    items_list = list(iva_summary.items())
                    
                    # Ordenar - CORRIGIDO
                    items_list.sort(key=lambda x: tax_order.get(x[0].split()[0], 99))
                    
                    for tax_key, valores in items_list:
                        linha = (
                            f"{tax_key:<6} "
                            f"{self.formatar_moeda(valores['base_sem_iva'], False):>12} "
                            f"{self.formatar_moeda(valores['valor_iva'], False):>12} "
                            f"{self.formatar_moeda(valores['total_com_iva'], False):>12}"
                        )
                        lines.append(linha)
                    
                    # Totais
                    total_base = sum(v['base_sem_iva'] for v in iva_summary.values())
                    total_iva = sum(v['valor_iva'] for v in iva_summary.values())
                    total_com_iva = sum(v['total_com_iva'] for v in iva_summary.values())
                    
                    lines.append("-" * line_width)
                    totals_line = (
                        f"{'TOTAL':<6} "
                        f"{self.formatar_moeda(total_base, False):>12} "
                        f"{self.formatar_moeda(total_iva, False):>12} "
                        f"{self.formatar_moeda(total_com_iva, False):>12}"
                    )
                    lines.append(totals_line)
                    lines.append("-" * line_width)
                    
            except Exception as e:
                self.logger.error(f"Erro ao gerar resumo IVA: {e}")
        
        # Footer
        lines.append(" ")
        lines.append("OBRIGADO PELA SUA PREFERÊNCIA!".center(line_width))
        lines.append("VOLTE SEMPRE".center(line_width))
        
        lines.append(" ")
        lines.append("Documento fiscal válido".center(line_width))
        lines.append("Processado por programa certificado".center(line_width))
        
        lines.append("=" * line_width)
        
        return "\n".join(lines)
    
    def save_receipt(self, sale_data: Dict[str, Any], filename: str = None) -> Optional[str]:
        """Salvar recibo em arquivo - CORRIGIDO"""
        try:
            # Gerar nome do arquivo
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                doc_number = str(sale_data.get('numero_venda', 'recibo'))
                filename = f"recibos/{doc_number}_{timestamp}.txt"
            
            # Criar diretório
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            # Gerar texto
            receipt_text = self.generate_receipt_text(sale_data)
            
            # Salvar
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(receipt_text)
            
            self.logger.info(f"Recibo salvo: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar recibo: {e}")
            return None
    
    def print_receipt(self, sale_data: Dict[str, Any]):
        """Imprimir recibo - SIMPLIFICADO"""
        try:
            # Para testes, apenas salvar em arquivo
            filename = self.save_receipt(sale_data)
            
            if filename:
                self.logger.info(f"Recibo pronto para impressão: {filename}")
            
        except Exception as e:
            self.logger.error(f"Erro ao imprimir recibo: {e}")

# Instância global
receipt_generator = ReceiptGenerator()