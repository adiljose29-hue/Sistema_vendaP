# config_manager.py
import configparser
import os
from pathlib import Path
import logging
from typing import Any, Dict
from typing import Any, Dict, Optional, Tuple  # Adicionar se necessário

class ConfigManager:
    """Gerenciador avançado de configurações do sistema"""
    
    def __init__(self):
        self.system_config = configparser.ConfigParser()
        self.receipt_config = configparser.ConfigParser()
        self.config_paths = {
            'system': 'config.ini',
            'receipt': 'recibo_config.ini'
        }
        
        self.default_system_config = {
            'DATABASE': {
                'host': 'localhost',
                'port': '3306',
                'database': 'pdv_sge',
                'username': 'root',
                'password': '',
                'reconnect_attempts': '5',
                'reconnect_delay': '3'
            },
            'PDV': {
                'pdv_id': '001',
                'loja_id': '0001',
                'empresa_id': '1',
                'pdv_numero': '1',
                'pdv_descricao': 'CAIXA 001'
            },
            'PRINTER': {
                'type': 'windows',  # windows, usb, com, ethernet, esc_pos
                'port': 'LPT1',
                'baudrate': '9600',
                'open_drawer': 'True',
                'paper_cut': 'True',
                'auto_print': 'True'
            },
            'CURRENCY': {
                'code': 'AOA',
                'symbol': 'Kz',
                'decimal_separator': ',',
                'thousands_separator': '.',
                'show_iva': 'True'
            },
            'SYSTEM': {
                'auto_reconnect': 'True',
                'log_level': 'INFO',
                'backup_interval': '3600',
                'cache_enabled': 'True',
                'cache_ttl': '300'
            },
            'AUTH': {
                'max_login_attempts': '3',
                'session_timeout': '3600',
                'password_length': '5',
                'worker_id_length': '4'
            }
        }
        
        self.default_receipt_config = {
            'HEADER': {
                'print_logo': 'True',
                'company_name': 'True',
                'company_address': 'True',
                'nif': 'True',
                'phone': 'True'
            },
            'BODY': {
                'bold_items': 'True',
                'align_center': 'True',
                'show_iva_summary': 'True',
                'print_timestamp': 'True',
                'show_payment_method': 'True'
            },
            'FOOTER': {
                'print_thankyou': 'True',
                'print_fiscal_info': 'True',
                'qr_code': 'True',
                'hash_document': 'True',
                'operator_info': 'True'
            },
            'FORMATTING': {
                'font_size': '12',
                'line_width': '42',
                'margin_left': '2',
                'margin_right': '2'
            }
        }
        
        self._initialize_configs()
    
    def _initialize_configs(self):
        """Inicializa arquivos de configuração com valores padrão"""
        for config_type, path in self.config_paths.items():
            if not os.path.exists(path):
                self._create_default_config(config_type)
            self._load_config(config_type)
    
    def _create_default_config(self, config_type: str):
        """Cria arquivo de configuração com valores padrão"""
        config = configparser.ConfigParser()
        
        if config_type == 'system':
            config.read_dict(self.default_system_config)
        elif config_type == 'receipt':
            config.read_dict(self.default_receipt_config)
        
        with open(self.config_paths[config_type], 'w', encoding='utf-8') as f:
            config.write(f)
    
    def _load_config(self, config_type: str):
        """Carrega configuração do arquivo"""
        config_file = configparser.ConfigParser()
        config_file.read(self.config_paths[config_type], encoding='utf-8')
        
        if config_type == 'system':
            self.system_config = config_file
        elif config_type == 'receipt':
            self.receipt_config = config_file
    
    # config_manager.py - Atualizar método get
    # config_manager.py - Correção do método get
    # config_manager.py - Método get completo e correto

    # config_manager.py - Método get() simplificado e correto

    def get(self, section: str, key: str, fallback: str = '') -> str:
        """Obtém valor de configuração com fallback - VERSÃO CORRIGIDA"""
        try:
            # Primeiro tenta no system_config
            if self.system_config.has_section(section):
                return self.system_config.get(section, key, fallback=fallback)
            # Tenta nos defaults
            elif section in self.default_system_config and key in self.default_system_config[section]:
                return self.default_system_config[section][key]
            else:
                return fallback
        except Exception as e:
            print(f"Erro no config.get({section}, {key}): {e}")
            return fallback
    
    def set(self, section: str, key: str, value: str, config_type: str = 'system'):
        """Define valor de configuração"""
        if config_type == 'system':
            if not self.system_config.has_section(section):
                self.system_config.add_section(section)
            self.system_config.set(section, key, value)
            
            with open(self.config_paths['system'], 'w', encoding='utf-8') as f:
                self.system_config.write(f)
        
        elif config_type == 'receipt':
            if not self.receipt_config.has_section(section):
                self.receipt_config.add_section(section)
            self.receipt_config.set(section, key, value)
            
            with open(self.config_paths['receipt'], 'w', encoding='utf-8') as f:
                self.receipt_config.write(f)
    
    def get_pdv_config(self) -> Dict[str, Any]:
        """Obtém configuração específica do PDV"""
        return {
            'pdv_id': self.get('PDV', 'pdv_id'),
            'loja_id': self.get('PDV', 'loja_id'),
            'empresa_id': self.get('PDV', 'empresa_id'),
            'pdv_numero': int(self.get('PDV', 'pdv_numero')),
            'pdv_descricao': self.get('PDV', 'pdv_descricao')
        }
    
    def get_database_config(self) -> Dict[str, Any]:
        """Obtém configuração do banco de dados"""
        return {
            'host': self.get('DATABASE', 'host'),
            'port': int(self.get('DATABASE', 'port')),
            'database': self.get('DATABASE', 'database'),
            'username': self.get('DATABASE', 'username'),
            'password': self.get('DATABASE', 'password'),
            'reconnect_attempts': int(self.get('DATABASE', 'reconnect_attempts')),
            'reconnect_delay': int(self.get('DATABASE', 'reconnect_delay'))
        }
    
    def get_printer_config(self) -> Dict[str, Any]:
        """Obtém configuração da impressora"""
        return {
            'type': self.get('PRINTER', 'type'),
            'port': self.get('PRINTER', 'port'),
            'baudrate': int(self.get('PRINTER', 'baudrate')),
            'open_drawer': self.get('PRINTER', 'open_drawer').lower() == 'true',
            'paper_cut': self.get('PRINTER', 'paper_cut').lower() == 'true',
            'auto_print': self.get('PRINTER', 'auto_print').lower() == 'true'
        }
    
    def get_currency_config(self) -> Dict[str, Any]:
        """Obtém configuração de moeda"""
        return {
            'code': self.get('CURRENCY', 'code'),
            'symbol': self.get('CURRENCY', 'symbol'),
            'decimal_separator': self.get('CURRENCY', 'decimal_separator'),
            'thousands_separator': self.get('CURRENCY', 'thousands_separator'),
            'show_iva': self.get('CURRENCY', 'show_iva').lower() == 'true'
        }
    
    def reload_configs(self):
        """Recarrega todas as configurações"""
        for config_type in self.config_paths.keys():
            self._load_config(config_type)


    def getboolean(self, section: str, key: str, fallback: bool = False) -> bool:
        """Obter valor booleano de configuração"""
        try:
            value = self.get(section, key, 'system')
            if value.lower() in ['true', '1', 'yes', 'on']:
                return True
            elif value.lower() in ['false', '0', 'no', 'off']:
                return False
            else:
                return fallback
        except:
            return fallback
    
    # ADICIONAR TAMBÉM getint e getfloat:
    def getint(self, section: str, key: str, fallback: int = 0) -> int:
        """Obter valor inteiro de configuração"""
        try:
            value = self.get(section, key, 'system')
            return int(value)
        except:
            return fallback
    
    def getfloat(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Obter valor float de configuração"""
        try:
            value = self.get(section, key, 'system')
            return float(value)
        except:
            return fallback



# Instância global
config = ConfigManager()