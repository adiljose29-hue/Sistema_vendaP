# scanner_manager.py 
import threading
import time
import queue
from typing import Callable, Optional
import logging

class ScannerManager:
    """Gerenciador de scanner para Tkinter"""
    
    def __init__(self, root_window=None):
        self.callback = None
        self.root = root_window
        self.scan_buffer = ""
        self.last_char_time = 0
        self.scan_timeout = 0.05  # 50ms entre caracteres
        self.running = True
        
        # Configurar logging
        self.logger = logging.getLogger('ScannerManager')
        
        if self.root:
            # Configurar bind global no Tkinter
            self._setup_tkinter_bind()
        else:
            # Modo fallback
            self._setup_fallback()
    
    def _setup_tkinter_bind(self):
        """Configurar captura de teclado no Tkinter"""
        try:
            # Bind global para capturar todas as teclas
            self.root.bind_all('<Key>', self._on_key_press)
            self.logger.info("Scanner configurado com Tkinter bind")
        except Exception as e:
            self.logger.error(f"Erro ao configurar bind Tkinter: {e}")
            self._setup_fallback()
    
    def _setup_fallback(self):
        """Configurar modo fallback"""
        self.logger.warning("Usando modo fallback para scanner")
    
    def _on_key_press(self, event):
        """Processar pressionamento de tecla para scanner"""
        try:
            char = event.char
            
            # Ignorar teclas especiais sem caractere
            if not char or len(char) == 0:
                return
            
            current_time = time.time()
            
            # Se passou muito tempo desde o último caractere, começar novo código
            if current_time - self.last_char_time > self.scan_timeout:
                if self.scan_buffer:
                    self.logger.debug(f"Código incompleto descartado: {self.scan_buffer}")
                self.scan_buffer = ""
            
            # Adicionar caractere ao buffer
            self.scan_buffer += char
            self.last_char_time = current_time
            
            # Scanners normalmente enviam Enter no final
            if char == '\r' or char == '\n':
                code = self.scan_buffer.strip()
                
                # CORRIGIR: Completar código se tiver menos de 13 dígitos
                if code and code.isdigit():
                    code_length = len(code)
                    
                    # Se código muito curto, pode ser apenas parte
                    if 5 <= code_length < 13:
                        self.logger.warning(f"Código curto detectado: {code} ({code_length} dígitos)")
                        
                        # Tentar completar com zeros à esquerda para EAN-13
                        if code_length == 5 or code_length == 8:
                            # Pode ser código interno (5 dígitos) ou EAN-8 (8 dígitos)
                            # Para EAN-13, completar com zeros à esquerda
                            code_completo = code.zfill(13)
                            self.logger.info(f"Código completado para EAN-13: {code_completo}")
                            code = code_completo
                        elif code_length == 12:
                            # Pode ser UPC-A sem dígito verificador
                            # Adicionar dígito verificador
                            code = self._calculate_check_digit(code)
                    
                    elif code_length > 13:
                        # Código muito longo, pegar últimos 13 dígitos
                        code = code[-13:]
                        self.logger.info(f"Código truncado para 13 dígitos: {code}")
                
                if code and len(code) >= 3:  # Pelo menos 3 caracteres
                    self.logger.info(f"Código processado: {code} (original: {self.scan_buffer})")
                    
                    # Chamar callback
                    if self.callback:
                        self.callback(code)
                
                self.scan_buffer = ""
                
        except Exception as e:
            self.logger.error(f"Erro ao processar tecla: {e}")
    
    def _calculate_check_digit(self, code: str) -> str:
        """Calcular dígito verificador para EAN-13"""
        if len(code) == 12:
            # Cálculo do dígito verificador EAN-13
            sum_even = sum(int(code[i]) for i in range(1, 12, 2))
            sum_odd = sum(int(code[i]) for i in range(0, 12, 2))
            total = sum_odd * 3 + sum_even
            check_digit = (10 - (total % 10)) % 10
            return code + str(check_digit)
        return code
        
    def set_callback(self, callback: Callable):
        """Definir função de callback"""
        self.callback = callback
        self.logger.info("Callback do scanner definido")
    
    def simulate_scan(self, code: str):
        """Simular escaneamento"""
        self.logger.info(f"Simulando escaneamento: {code}")
        if self.callback:
            self.callback(code)
    
    def stop(self):
        """Parar scanner"""
        self.running = False
        if self.root:
            try:
                self.root.unbind_all('<Key>')
            except:
                pass
        self.logger.info("Scanner manager parado")

# Instância será criada no POS.py
scanner_manager = None