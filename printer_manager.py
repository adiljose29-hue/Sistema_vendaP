# printer_manager.py
import threading
import queue
import time
from typing import Dict, Any, Optional
import logging
from config_manager import config
from typing import Dict, Any, Optional, Tuple

class PrinterManager:
    """Gerenciador avançado de impressão"""
    
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
        self.print_queue = queue.Queue()
        self.printing = False
        
        # Configurar logging
        self.logger = logging.getLogger('PrinterManager')
        self._setup_logging()
        
        # Iniciar thread de impressão
        self._start_print_thread()
    
    def _setup_logging(self):
        """Configurar sistema de logs"""
        if not self.logger.handlers:
            handler = logging.FileHandler('logs/printer.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    
    
    def print_receipt(self, sale_data: Dict[str, Any], auto_print: bool = None):
        """Adicionar recibo à fila de impressão"""
        if auto_print is None:
            auto_print = config.getboolean('PRINTER', 'auto_print', fallback=True)
        
        if not auto_print:
            self.logger.info("Impressão automática desativada")
            return
        
        print_job = {
            'type': 'receipt',
            'data': sale_data,
            'timestamp': time.time()
        }
        
        self.print_queue.put(print_job)
        self.logger.info("Recibo adicionado à fila de impressão")
    
    def print_test_page(self):
        """Imprimir página de teste"""
        print_job = {
            'type': 'test',
            'timestamp': time.time()
        }
        
        self.print_queue.put(print_job)
        self.logger.info("Página de teste adicionada à fila")
    
    def _print_test_page(self):
        """Imprimir página de teste"""
        test_text = """
        ==========================================
                    TESTE DE IMPRESSÃO
        ==========================================
        Sistema PDV - Fujitsu ISSXXI
        Data: {date}
        Hora: {time}
        ==========================================
        Este é um teste de impressão.
        Se esta página foi impressa corretamente,
        a impressora está configurada adequadamente.
        ==========================================
        """.format(
            date=time.strftime("%d/%m/%Y"),
            time=time.strftime("%H:%M:%S")
        )
        
        # Usar receipt_generator para imprimir
        from receipt_generator import receipt_generator
        receipt_data = {
            'numero_documento': 'TESTE',
            'data_emissao': time.strftime("%d/%m/%Y %H:%M"),
            'operador_nome': 'SISTEMA',
            'itens': [],
            'total_venda': 0,
            'total_pago': 0,
            'troco': 0,
            'forma_pagamento': 'TESTE'
        }
        
        receipt_generator.print_receipt(receipt_data)
    
    def _print_report(self, report_data: Dict[str, Any]):
        """Imprimir relatório"""
        # Implementar lógica de impressão de relatórios
        pass
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Obter status da fila de impressão"""
        return {
            'queue_size': self.print_queue.qsize(),
            'printing': self.printing
        }

    def _start_print_thread(self):
        """Iniciar thread de impressão"""
        def print_worker():
            self.logger.info("Thread de impressão iniciada")
            
            while True:
                try:
                    print_job = self.print_queue.get()
                    
                    if print_job is None:
                        break
                    
                    self._process_print_job(print_job)
                    self.print_queue.task_done()
                    
                except Exception as e:
                    self.logger.error(f"Erro na thread de impressão: {e}")
        
        thread = threading.Thread(target=print_worker, daemon=True)
        thread.start()
    
    def _process_print_job(self, print_job: Dict[str, Any]):
        """Processar trabalho de impressão"""
        try:
            printer_type = config.get('PRINTER', 'type', 'system', 'file').lower()
            
            if printer_type == 'windows':
                self._print_windows(print_job)
            elif printer_type == 'esc_pos':
                self._print_esc_pos(print_job)
            elif printer_type == 'com':
                self._print_serial(print_job)
            elif printer_type == 'ethernet':
                self._print_ethernet(print_job)
            elif printer_type == 'file':
                self._print_to_file(print_job)
            else:
                self.logger.error(f"Tipo de impressora não suportado: {printer_type}")
                # Fallback para arquivo
                self._print_to_file(print_job)
            
            self.logger.info(f"Documento impresso: {print_job.get('type', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Erro ao imprimir: {e}")
    
    # printer_manager.py - Corrigir também as chamadas de config.get()

    def _print_windows(self, print_job: Dict[str, Any]):
        """Imprimir em impressora Windows - CORRIGIDO"""
        try:
            import tempfile
            import os
            
            receipt_text = print_job.get('text', '')
            if not receipt_text:
                from receipt_generator import receipt_generator
                receipt_text = receipt_generator.generate_receipt_text(print_job.get('data', {}))
            
            # Obter nome da impressora - CORRIGIDO
            printer_name = config.get('PRINTER', 'windows_printer_name', fallback='')  # CORRIGIDO
            if not printer_name:
                try:
                    import win32print
                    printer_name = win32print.GetDefaultPrinter()
                except ImportError:
                    printer_name = ''
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', 
                                           delete=False, encoding='utf-8') as f:
                f.write(receipt_text)
                temp_file = f.name
            
            # Imprimir
            if printer_name:
                try:
                    import win32api
                    win32api.ShellExecute(
                        0,              # hwnd
                        "print",        # operation
                        temp_file,      # file
                        f'"{printer_name}"',  # parameters
                        ".",            # directory
                        0               # show command
                    )
                except ImportError:
                    # Método alternativo
                    import subprocess
                    command = f'print /D:"{printer_name}" "{temp_file}"'
                    subprocess.run(command, shell=True, check=False)
            else:
                import subprocess
                command = f'print "{temp_file}"'
                subprocess.run(command, shell=True, check=False)
            
            # Aguardar e limpar
            time.sleep(2)
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            
            self.logger.info(f"Impresso em impressora Windows: {printer_name}")
            
        except Exception as e:
            self.logger.error(f"Erro na impressão Windows: {e}")
            raise
        
    def _open_cash_drawer(self):
        """Abrir gaveta de dinheiro"""
        try:
            printer_type = config.get('PRINTER', 'type', 'windows').lower()
            
            if printer_type == 'esc_pos':
                import serial
                
                port = config.get('PRINTER', 'port', 'COM1')
                baudrate = config.getint('PRINTER', 'baudrate', 9600)
                
                printer = serial.Serial(port=port, baudrate=baudrate, timeout=1)
                printer.write(b'\x1B\x70\x00\x19\x19')  # Comando abrir gaveta
                printer.close()
                
                self.logger.info(f"Gaveta aberta em {port}")
                
            elif printer_type == 'windows':
                # Para impressoras Windows com porta serial
                self._print_esc_pos({'type': 'open_drawer'})
                
            self.logger.info("Gaveta aberta com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao abrir gaveta: {e}")
            raise
    
    def _print_windows_alt(self, print_job: Dict[str, Any]):
        """Método alternativo para Windows"""
        try:
            import subprocess
            import tempfile
            import os
            
            receipt_text = print_job.get('text', '')
            if not receipt_text:
                from receipt_generator import receipt_generator
                receipt_text = receipt_generator.generate_receipt_text(print_job.get('data', {}))
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', 
                                           delete=False, encoding='utf-8') as f:
                f.write(receipt_text)
                temp_file = f.name
            
            # Comando print do Windows
            printer_name = config.get('PRINTER', 'windows_printer_name', fallback='')
            
            if printer_name:
                command = f'print /D:"{printer_name}" "{temp_file}"'
            else:
                command = f'print "{temp_file}"'
            
            subprocess.run(command, shell=True, check=False)
            
            # Limpar
            time.sleep(1)
            os.unlink(temp_file)
            
        except Exception as e:
            self.logger.error(f"Erro na impressão Windows: {e}")
            raise
    
    def _print_esc_pos(self, print_job: Dict[str, Any]):
        """Imprimir em impressora ESC/POS"""
        try:
            import serial
            
            receipt_text = print_job.get('text', '')
            if not receipt_text:
                from receipt_generator import receipt_generator
                receipt_text = receipt_generator.generate_receipt_text(print_job.get('data', {}))
            
            port = config.get('PRINTER', 'port', 'COM1')
            baudrate = config.getint('PRINTER', 'baudrate', 9600)
            
            printer = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            
            # Comandos ESC/POS
            printer.write(b'\x1B\x40')  # Initialize
            printer.write(b'\x1B\x21\x00')  # Default font
            
            # Imprimir texto
            printer.write(receipt_text.encode('cp850', errors='replace'))
            
            # Avançar papel
            printer.write(b'\n\n\n')
            
            # Cortar papel (se configurado)
            if config.getboolean('PRINTER', 'paper_cut', True):
                printer.write(b'\x1D\x56\x41\x10')  # Full cut
            
            # Abrir gaveta (se configurado)
            if config.getboolean('PRINTER', 'open_drawer', True):
                printer.write(b'\x1B\x70\x00\x19\x19')  # Pulse drawer
            
            time.sleep(0.5)
            printer.close()
            
            self.logger.info(f"Impresso ESC/POS em {port}")
            
        except Exception as e:
            self.logger.error(f"Erro na impressão ESC/POS: {e}")
            raise
    
    def _print_serial(self, print_job: Dict[str, Any]):
        """Imprimir em porta serial (COM)"""
        # Similar ao ESC/POS mas mais genérico
        self._print_esc_pos(print_job)
    
    def _print_ethernet(self, print_job: Dict[str, Any]):
        """Imprimir em impressora Ethernet"""
        try:
            import socket
            
            receipt_text = print_job.get('text', '')
            if not receipt_text:
                from receipt_generator import receipt_generator
                receipt_text = receipt_generator.generate_receipt_text(print_job.get('data', {}))
            
            ip = config.get('PRINTER', 'ethernet_ip', '192.168.1.100')
            port = config.getint('PRINTER', 'ethernet_port', 9100)
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((ip, port))
            
            sock.send(receipt_text.encode('utf-8'))
            
            # Comandos adicionais
            sock.send(b'\n\n\n')  # Line feeds
            
            if config.getboolean('PRINTER', 'paper_cut', True):
                sock.send(b'\x1D\x56\x41\x10')  # Cut
            
            sock.close()
            
            self.logger.info(f"Impresso via Ethernet em {ip}:{port}")
            
        except Exception as e:
            self.logger.error(f"Erro na impressão Ethernet: {e}")
            raise
    
    def _print_to_file(self, print_job: Dict[str, Any]):
        """Salvar em arquivo (para testes)"""
        from receipt_generator import receipt_generator
        
        sale_data = print_job.get('data', {})
        filename = receipt_generator.save_receipt(sale_data)
        
        self.logger.info(f"Documento salvo em arquivo: {filename}")
    
    def print_receipt(self, sale_data: Dict[str, Any]):
        """Adicionar recibo à fila de impressão"""
        if not config.getboolean('PRINTER', 'auto_print', True):
            self.logger.info("Impressão automática desativada")
            return
        
        print_job = {
            'type': 'receipt',
            'data': sale_data,
            'timestamp': time.time(),
            'copies': sale_data.get('copies', 1)
        }
        
        # Adicionar múltiplas cópias se necessário
        copies = sale_data.get('copies', 1)
        for i in range(copies):
            self.print_queue.put(print_job.copy())
            self.logger.info(f"Cópia {i+1}/{copies} adicionada à fila")



# Instância global
printer_manager = PrinterManager()