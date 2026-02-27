# POS.py 
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from datetime import datetime as dt  # Renomear para evitar conflito
import threading
import time
from typing import Dict, List, Optional, Any
# Adicionar esta linha após as outras importações
from decimal import Decimal
import queue
import sys
import os

# Adicionar diretório atual ao path para importar módulos locais
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar módulos locais
from config_manager import config
from connection_manager import connection_pool
from product_cache import product_cache
from auth_manager import auth_manager
from database import DatabaseManager
from document_manager import document_manager
from receipt_generator import receipt_generator
from printer_manager import printer_manager

#Importar scanner_manager CONDICIONALMENTE (pode não existir ainda)
try:
    from scanner_manager import scanner_manager
    SCANNER_AVAILABLE = True
except ImportError:
    SCANNER_AVAILABLE = False
    # Criar um placeholder para evitar erros
    class DummyScannerManager:
        def set_callback(self, callback):
            pass
        def simulate_scan(self, code):
            pass
    scanner_manager = DummyScannerManager()


class ProfessionalPDV:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema PDV - Fujitsu ISSXXI")
        self.root.geometry("1300x850")
        self.root.configure(bg='#1a1a2e')
        
        # PRIMEIRO configurar logging
        self._setup_logging()
        self.logger.info("Inicializando sistema PDV...")
        
        # Carregar configurações
        self.pdv_config = config.get_pdv_config()
        self.currency_config = config.get_currency_config()
        
        # Estado do sistema
        self.modo_atual = 'login'  # login, venda, pagamento, funcoes, sangria, devolucao
        self.sessao_atual = None
        self.carrinho = []
        self.input_buffer = ""
        self.scan_buffer = ""
        self.ultimo_produto = None
        self.quantidade_pendente = None
        
        # Display
        self.display_lines = ["", "", ""]
        
        # Conexão
        self.conexao_status = False
        self.last_connection_check = time.time()
        
        # Filas para comunicação entre threads
        self.scan_queue = queue.Queue()
        self.print_queue = queue.Queue()
        
        # Cores por modo
        self.modo_cores = {
            'login': {'bg': '#1a1a2e', 'fg': '#e94560', 'name': 'MODO LOGIN'},
            'venda': {'bg': '#1a1a2e', 'fg': '#00b894', 'name': 'MODO VENDA'},
            'pagamento': {'bg': '#1a1a2e', 'fg': '#6c5ce7', 'name': 'MODO PAGAMENTO'},
            'funcoes': {'bg': '#1a1a2e', 'fg': '#fdcb6e', 'name': 'MODO FUNÇÕES'},
            'sangria': {'bg': '#1a1a2e', 'fg': '#d63031', 'name': 'MODO SANGRIA'},
            'devolucao': {'bg': '#1a1a2e', 'fg': '#e84393', 'name': 'MODO DEVOLUÇÃO'}
        }
        
        # Cores modernas
        self.cores = {
            'fundo_escuro': '#1a1a2e',
            'fundo_medio': '#16213e',
            'fundo_card': '#0f3460',
            'destaque': '#e94560',
            'sucesso': '#00b894',
            'alerta': '#fdcb6e',
            'erro': '#d63031',
            'texto_primario': '#ffffff',
            'texto_secundario': '#b2bec3',
            'botao_primario': '#6c5ce7',
            'botao_secundario': '#a29bfe'
        }
        
        # Configurar callback do scanner (se disponível)
        # if SCANNER_AVAILABLE:
            # scanner_manager.set_callback(self.handle_scanned_code)
            # self.logger.info("Scanner manager configurado")
        # else:
            # self.logger.warning("Scanner manager não disponível")
         # Inicializar scanner COM a janela root
        global scanner_manager
        from scanner_manager import ScannerManager
        scanner_manager = ScannerManager(root)
        scanner_manager.set_callback(self.handle_scanned_code)
        
        # Configurar callback do scanner
        try:
            from scanner_manager import ScannerManager
            scanner_manager = ScannerManager(self.root)  # CORRIGIDO: usar self.root
            scanner_manager.set_callback(self.handle_scanned_code)
            SCANNER_AVAILABLE = True
            self.logger.info("Scanner manager configurado")
        except ImportError as e:
            SCANNER_AVAILABLE = False
            self.logger.warning(f"Scanner manager não disponível: {e}")
            # Criar um placeholder
            class DummyScannerManager:
                def set_callback(self, callback):
                    pass
                def simulate_scan(self, code):
                    pass
            scanner_manager = DummyScannerManager()
            
        # Criar diretórios necessários
        diretorios = ['logs', 'recibos', 'comprovativos']
        for diretorio in diretorios:
            os.makedirs(diretorio, exist_ok=True)
        
        # Inicializar componentes
        self._setup_connection_monitor()
        
        # Criar interface
        self.criar_interface()
        
        # Inicializar estado
        self.atualizar_modo('login')
        self.atualizar_display()
        
    def _setup_logging(self):
        """Configurar sistema de logs"""
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/system.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('PDV')
        
    def _setup_scanner_listener(self):
        """Configurar listener para scanner de código de barras"""
        # Esta função será expandida para capturar entrada do scanner
        pass
    
    def _setup_connection_monitor(self):
        """Iniciar monitor de conexão"""
        def monitor():
            while True:
                try:
                    self._check_connection()
                    time.sleep(5)  # Verificar a cada 5 segundos
                except Exception as e:
                    self.logger.error(f"Erro no monitor de conexão: {e}")
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
    
    def _check_connection(self):
        """Verificar status da conexão"""
        current_time = time.time()
        if current_time - self.last_connection_check > 5:
            self.last_connection_check = current_time
            old_status = self.conexao_status
            self.conexao_status = connection_pool.test_connection()
            
            if old_status != self.conexao_status:
                status_text = "CONECTADO" if self.conexao_status else "DESCONECTADO"
                status_color = self.cores['sucesso'] if self.conexao_status else self.cores['erro']
                
                # Atualizar interface
                self.root.after(0, self._update_connection_status, status_text, status_color)
                
                self.logger.info(f"Status de conexão alterado: {status_text}")
    
    def _update_connection_status(self, status_text, status_color):
        """Atualizar status da conexão na interface"""
        if hasattr(self, 'label_conectado'):
            self.label_conectado.config(
                text=f"● {status_text}",
                fg=status_color
            )
    
    def criar_interface(self):
        """Criar interface principal"""
        # Frame principal
        main_frame = tk.Frame(self.root, bg=self.cores['fundo_escuro'])
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        # Cabeçalho moderno
        self.criar_cabecalho_moderno(main_frame)
        
        # Área central
        content_frame = tk.Frame(main_frame, bg=self.cores['fundo_medio'])
        content_frame.pack(fill='both', expand=True, pady=10)
        
        # Painel esquerdo - Display e produtos
        left_panel = tk.Frame(content_frame, bg=self.cores['fundo_medio'])
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 15))
        
        # Painel direito - Teclado e funções
        right_panel = tk.Frame(content_frame, bg=self.cores['fundo_medio'], width=500)
        right_panel.pack(side='right', fill='y')
        right_panel.pack_propagate(False)
        
        # Componentes
        self.criar_display_moderno(left_panel)
        self.criar_lista_produtos(left_panel)
        self.criar_painel_direito_moderno(right_panel)
        self.criar_rodape_moderno(main_frame)
        
        # Inicializar estado
        self.atualizar_modo('login')
        self.atualizar_display()
    
    def criar_cabecalho_moderno(self, parent):
        """Criar cabeçalho com informações do sistema"""
        header_frame = tk.Frame(parent, bg=self.cores['fundo_escuro'])
        header_frame.pack(fill='x', pady=(0, 10))
        
        # Título principal
        titulo_frame = tk.Frame(header_frame, bg=self.cores['fundo_escuro'])
        titulo_frame.pack(fill='x', pady=5)
        
        titulo = tk.Label(titulo_frame, text="ESC MARKET - PDV PROFISSIONAL", 
                         bg=self.cores['fundo_escuro'], fg=self.cores['texto_primario'], 
                         font=('Arial', 18, 'bold'))
        titulo.pack()
        
        subtitulo = tk.Label(titulo_frame, text="Sistema de Ponto de Venda Integrado", 
                            bg=self.cores['fundo_escuro'], fg=self.cores['texto_secundario'], 
                            font=('Arial', 10))
        subtitulo.pack()
        
        # Cartões de informação
        info_cards_frame = tk.Frame(header_frame, bg=self.cores['fundo_escuro'])
        info_cards_frame.pack(fill='x', pady=5)
        
        # Cartão Modo
        self.card_modo = self.criar_card_info(info_cards_frame, "MODO", "LOGIN", 
                                            self.modo_cores['login']['fg'], 0)
        
        # Cartão Artigos
        self.card_artigos = self.criar_card_info(info_cards_frame, "ARTIGOS", "0", 
                                               self.cores['botao_primario'], 1)
        
        # Cartão Total
        self.card_total = self.criar_card_info(info_cards_frame, "TOTAL VENDA", "Kz 0,00", 
                                             self.cores['destaque'], 2)
        
        # Cartão Cliente
        self.card_cliente = self.criar_card_info(info_cards_frame, "CLIENTE", "CONSUMIDOR FINAL", 
                                               self.cores['sucesso'], 3)
    
    def criar_card_info(self, parent, titulo, valor, cor, pos):
        """Criar cartão de informação"""
        card = tk.Frame(parent, bg=self.cores['fundo_card'], height=60)
        card.pack(side='left', fill='x', expand=True, padx=5)
        card.pack_propagate(False)
        
        label_titulo = tk.Label(card, text=titulo, bg=self.cores['fundo_card'], 
                               fg=self.cores['texto_secundario'], font=('Arial', 9))
        label_titulo.pack(pady=(8, 0))
        
        label_valor = tk.Label(card, text=valor, bg=self.cores['fundo_card'], 
                              fg=self.cores['texto_primario'], font=('Arial', 12, 'bold'))
        label_valor.pack(pady=(0, 8))
        
        return card
    
    def criar_display_moderno(self, parent):
        """Criar display de LED moderno"""
        display_main = tk.Frame(parent, bg=self.cores['fundo_card'])
        display_main.pack(fill='x', expand=False, padx=10, pady=10, ipady=10)
        
        # Display LED style
        display_frame = tk.Frame(display_main, bg='#0a0a1a', height=120)
        display_frame.pack(fill='x', padx=15, pady=15)
        display_frame.pack_propagate(False)
        
        # Efeito de borda LED
        border_frame = tk.Frame(display_frame, bg='#00ff00', height=2)
        border_frame.pack(fill='x')
        
        # Conteúdo do display
        display_content = tk.Frame(display_frame, bg='#0a0a1a')
        display_content.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Linhas do display
        self.display_line1 = tk.Label(display_content, text="", 
                                     bg='#0a0a1a', fg='#00ff00', 
                                     font=('Courier New', 14, 'bold'),
                                     anchor='w', justify='left')
        self.display_line1.pack(fill='x', padx=10, pady=(10, 5))
        
        self.display_line2 = tk.Label(display_content, text="", 
                                     bg='#0a0a1a', fg='#00ff00', 
                                     font=('Courier New', 12),
                                     anchor='w', justify='left')
        self.display_line2.pack(fill='x', padx=10, pady=(0, 5))
        
        self.display_line3 = tk.Label(display_content, text="", 
                                     bg='#0a0a1a', fg='#00ff00', 
                                     font=('Courier New', 11),
                                     anchor='w', justify='left')
        self.display_line3.pack(fill='x', padx=10, pady=(0, 10))
    
    def criar_lista_produtos(self, parent):
        """Criar lista de produtos em Treeview"""
        # Frame para lista de produtos
        produtos_frame = tk.Frame(parent, bg=self.cores['fundo_card'])
        produtos_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Header
        produtos_header = tk.Frame(produtos_frame, bg=self.cores['fundo_card'])
        produtos_header.pack(fill='x', padx=10, pady=(5, 0))
        
        tk.Label(produtos_header, text="PRODUTOS ADICIONADOS", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 11, 'bold')).pack(anchor='w')
        
        # Treeview
        tree_frame = tk.Frame(produtos_frame, bg=self.cores['fundo_card'])
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        columns = ('item', 'codigo', 'descricao', 'quantidade', 'preco', 'total', 'iva')
        self.tree_produtos = ttk.Treeview(tree_frame, columns=columns, 
                                         show='headings', height=12)
        
        # Configurar colunas
        col_configs = [
            ('item', 'ITEM', 50),
            ('codigo', 'CÓDIGO', 120),
            ('descricao', 'DESCRIÇÃO', 300),
            ('quantidade', 'QTD', 70),
            ('preco', 'PREÇO UNIT.', 100),
            ('total', 'TOTAL', 100),
            ('iva', 'IVA %', 60)
        ]
        
        for col, heading, width in col_configs:
            self.tree_produtos.heading(col, text=heading)
            self.tree_produtos.column(col, width=width, 
                                     anchor='center' if col in ['item', 'quantidade', 'iva'] else 'e')
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', 
                                 command=self.tree_produtos.yview)
        self.tree_produtos.configure(yscrollcommand=scrollbar.set)
        
        self.tree_produtos.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def criar_painel_direito_moderno(self, parent):
        """Criar painel direito com teclado e funções"""
        right_main = tk.Frame(parent, bg=self.cores['fundo_medio'])
        right_main.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Seção de teclado numérico
        teclado_frame = tk.Frame(right_main, bg=self.cores['fundo_medio'])
        teclado_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(teclado_frame, text="TECLADO NUMÉRICO", 
                bg=self.cores['fundo_medio'], fg=self.cores['texto_primario'], 
                font=('Arial', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        self.criar_teclado_numerico_moderno(teclado_frame)
        
        # Seção de botões de função
        funcoes_frame = tk.Frame(right_main, bg=self.cores['fundo_medio'])
        funcoes_frame.pack(fill='both', expand=True)
        
        tk.Label(funcoes_frame, text="FUNÇÕES DO SISTEMA", 
                bg=self.cores['fundo_medio'], fg=self.cores['texto_primario'],
                font=('Arial', 12, 'bold')).pack(anchor='w', pady=(0, 10))
        
        self.criar_botoes_funcao_dinamicos(funcoes_frame)
    
    def criar_teclado_numerico_moderno(self, parent):
        """Criar teclado numérico"""
        teclado_container = tk.Frame(parent, bg=self.cores['fundo_card'], 
                                    padx=10, pady=10)
        teclado_container.pack(fill='x', pady=5)
        
        teclas_frame = tk.Frame(teclado_container, bg=self.cores['fundo_card'])
        teclas_frame.pack(fill='x')
        
        # Layout do teclado
        teclas = [
            ['7', '8', '9', 'Qts'],
            ['4', '5', '6', 'Apagar'],
            ['1', '2', '3', 'Cancelar'],
            ['0', '00', ',', 'Enter']
        ]
        
        cores_especiais = {
            'Qts': self.cores['alerta'],
            'Apagar': self.cores['alerta'],
            'Cancelar': self.cores['erro'],
            'Enter': self.cores['sucesso']
        }
        
        for i, linha in enumerate(teclas):
            for j, tecla in enumerate(linha):
                bg_color = cores_especiais.get(tecla, self.cores['fundo_medio'])
                fg_color = '#ffffff' if tecla in cores_especiais else self.cores['texto_primario']
                font_size = 10 if tecla in cores_especiais else 12
                
                btn = tk.Button(teclas_frame, text=tecla,
                              bg=bg_color, fg=fg_color,
                              font=('Arial', font_size, 'bold'),
                              width=6 if tecla not in ['Cancelar', 'Enter'] else 8,
                              height=2,
                              command=lambda t=tecla: self.tecla_pressionada(t))
                btn.grid(row=i, column=j, padx=3, pady=3, sticky='nsew')
            
            teclas_frame.rowconfigure(i, weight=1)
        
        for j in range(4):
            teclas_frame.columnconfigure(j, weight=1)
    
    def criar_botoes_funcao_dinamicos(self, parent):
        """Criar botões de função com scroll"""
        # Frame principal com scroll
        main_frame = tk.Frame(parent, bg=self.cores['fundo_medio'])
        main_frame.pack(fill='both', expand=True)
        
        # Canvas para scrolling
        self.canvas_funcoes = tk.Canvas(main_frame, bg=self.cores['fundo_medio'], 
                                       highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient='vertical', 
                                 command=self.canvas_funcoes.yview)
        
        # Frame que vai dentro do canvas
        self.funcoes_container = tk.Frame(self.canvas_funcoes, bg=self.cores['fundo_medio'])
        
        # Configurar canvas
        self.canvas_funcoes.create_window((0, 0), window=self.funcoes_container, 
                                          anchor="nw", width=parent.winfo_width()-20)
        self.canvas_funcoes.configure(yscrollcommand=scrollbar.set)
        
        # Pack dos elementos
        self.canvas_funcoes.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind para redimensionar
        self.canvas_funcoes.bind('<Configure>', 
                               lambda e: self.canvas_funcoes.itemconfig(
                                   self.canvas_funcoes.find_all()[0], 
                                   width=e.width-20
                               ))
        
        # Bind do mouse wheel
        self._bind_mousewheel_scroll(self.canvas_funcoes)
        self._bind_mousewheel_scroll(self.funcoes_container)
        
        # Atualizar inicialmente
        self.funcoes_container.bind('<Configure>', 
                                  lambda e: self.canvas_funcoes.configure(
                                      scrollregion=self.canvas_funcoes.bbox("all")
                                  ))
    
    def _bind_mousewheel_scroll(self, widget):
        """Bind do mouse wheel para scrolling"""
        widget.bind("<MouseWheel>", self._on_mousewheel_funcoes)
        widget.bind("<Button-4>", self._on_mousewheel_funcoes)  # Linux
        widget.bind("<Button-5>", self._on_mousewheel_funcoes)  # Linux
    
    def _on_mousewheel_funcoes(self, event):
        """Scrolling com mouse wheel"""
        if event.delta:
            self.canvas_funcoes.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif event.num == 4:
            self.canvas_funcoes.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas_funcoes.yview_scroll(1, "units")
    
    def criar_rodape_moderno(self, parent):
        """Criar rodapé com informações do sistema"""
        rodape_frame = tk.Frame(parent, bg=self.cores['fundo_escuro'])
        rodape_frame.pack(fill='x', pady=(15, 0))
        
        # Informações da sessão
        sessao_frame = tk.Frame(rodape_frame, bg=self.cores['fundo_card'])
        sessao_frame.pack(fill='x', pady=5)
        
        # Data e hora
        self.label_data_hora = tk.Label(sessao_frame, text="", 
                                       bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                                       font=('Arial', 10, 'bold'))
        self.label_data_hora.pack(side='right', padx=15, pady=8)
        self.atualizar_data_hora()
        
        # Informações do sistema
        info_sistema = [
            ("🏪 LOJA", self.pdv_config['loja_id']),
            ("💻 CAIXA", self.pdv_config['pdv_id']),
            ("👤 OPERADOR", "AGUARDANDO LOGIN"),
            ("🔢 SÉRIE", "PDV-001"),
            ("● STATUS", "AGUARDANDO")
        ]
        
        self.info_widgets = []
        for i, (icone, valor) in enumerate(info_sistema):
            info_item = tk.Frame(sessao_frame, bg=self.cores['fundo_card'])
            info_item.pack(side='left', padx=15, pady=8)
            
            label_icone = tk.Label(info_item, text=icone, bg=self.cores['fundo_card'],
                                  fg=self.cores['texto_secundario'], font=('Arial', 9))
            label_icone.pack(anchor='w')
            
            label_valor = tk.Label(info_item, text=valor, bg=self.cores['fundo_card'],
                                  fg=self.cores['texto_primario'], font=('Arial', 9, 'bold'))
            label_valor.pack(anchor='w')
            
            self.info_widgets.append(label_valor)
        
        # Status bar
        status_bar = tk.Frame(rodape_frame, bg=self.cores['fundo_medio'], height=30)
        status_bar.pack(fill='x', pady=(5, 0))
        status_bar.pack_propagate(False)
        
        tk.Label(status_bar, 
                text="Sistema PDV Fujitsu ISSXXI © 2024 - Todos os direitos reservados",
                bg=self.cores['fundo_medio'], fg=self.cores['texto_secundario'],
                font=('Arial', 9)).pack(side='left', padx=10, pady=5)
        
        self.label_conectado = tk.Label(status_bar, text="● CONECTANDO...", fg=self.cores['alerta'],
                                       bg=self.cores['fundo_medio'], font=('Arial', 9, 'bold'))
        self.label_conectado.pack(side='right', padx=10, pady=5)
    
        # Status bar - ADICIONAR BOTÃO DE IMPRESSORA
        status_bar = tk.Frame(rodape_frame, bg=self.cores['fundo_medio'], height=30)
        status_bar.pack(fill='x', pady=(5, 0))
        status_bar.pack_propagate(False)
        
        # Botão de configuração da impressora
        btn_impr_config = tk.Button(status_bar, text="🖨️",
                                  bg=self.cores['botao_primario'], fg='white',
                                  font=('Arial', 10),
                                  width=3, height=1,
                                  command=self.configurar_impressora)
        btn_impr_config.pack(side='left', padx=(10, 5), pady=2)
        
        tk.Label(status_bar, 
                text="Sistema PDV Fujitsu ISSXXI © 2024",
                bg=self.cores['fundo_medio'], fg=self.cores['texto_secundario'],
                font=('Arial', 9)).pack(side='left', padx=5, pady=5)
        
        # Status da impressora
        self.label_status_impressora = tk.Label(status_bar, 
                                              text="🖨️ OK", 
                                              fg=self.cores['sucesso'],
                                              bg=self.cores['fundo_medio'], 
                                              font=('Arial', 9))
        self.label_status_impressora.pack(side='left', padx=5, pady=5)
        
        self.label_conectado = tk.Label(status_bar, 
                                       text="● CONECTADO", 
                                       fg=self.cores['sucesso'],
                                       bg=self.cores['fundo_medio'], 
                                       font=('Arial', 9, 'bold'))
        self.label_conectado.pack(side='right', padx=10, pady=5)
    

    def configurar_impressora(self):
        """Abrir configuração da impressora - MELHORADO"""
        config_window = tk.Toplevel(self.root)
        config_window.title("Configuração da Impressora")
        config_window.geometry("600x500")
        config_window.configure(bg=self.cores['fundo_medio'])
        config_window.transient(self.root)
        config_window.grab_set()
        
        # Centralizar janela
        config_window.update_idletasks()
        width = config_window.winfo_width()
        height = config_window.winfo_height()
        x = (config_window.winfo_screenwidth() // 2) - (width // 2)
        y = (config_window.winfo_screenheight() // 2) - (height // 2)
        config_window.geometry(f'{width}x{height}+{x}+{y}')
        
        # Título
        tk.Label(config_window, text="CONFIGURAÇÃO DA IMPRESSORA",
                bg=self.cores['fundo_medio'], fg=self.cores['texto_primario'],
                font=('Arial', 14, 'bold')).pack(pady=10)
        
        # Frame de configuração com scroll
        main_frame = tk.Frame(config_window, bg=self.cores['fundo_medio'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main_frame, bg=self.cores['fundo_medio'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.cores['fundo_card'], padx=20, pady=20)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Tipos de impressora
        row = 0
        tk.Label(scrollable_frame, text="Tipo de Impressora:", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        
        tipos = [
            ('windows', 'Windows (impressora padrão)'),
            ('esc_pos', 'ESC/POS (USB/Serial)'),
            ('com', 'Porta COM/LPT'),
            ('ethernet', 'Ethernet/TCP-IP'),
            ('file', 'Arquivo (para testes)')
        ]
        
        self.var_tipo_impressora = tk.StringVar(value=config.get('PRINTER', 'type', fallback='windows'))
        
        for i, (codigo, descricao) in enumerate(tipos):
            rb = tk.Radiobutton(scrollable_frame, text=descricao, 
                              variable=self.var_tipo_impressora, value=codigo,
                              bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                              selectcolor=self.cores['fundo_medio'],
                              command=self._atualizar_campos_impressora)
            rb.grid(row=row, column=1, columnspan=2, sticky='w', padx=20, pady=5)
            row += 1
        
        # Frame para campos dinâmicos
        self.campos_impressora_frame = tk.Frame(scrollable_frame, bg=self.cores['fundo_card'])
        self.campos_impressora_frame.grid(row=row, column=0, columnspan=3, sticky='ew', pady=10)
        row += 1
        
        # Para Windows
        self.frame_windows = tk.Frame(self.campos_impressora_frame, bg=self.cores['fundo_card'])
        tk.Label(self.frame_windows, text="Nome da Impressora Windows:", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario']).pack(anchor='w', pady=5)
        
        self.entry_printer_name = tk.Entry(self.frame_windows, width=40, font=('Arial', 10))
        self.entry_printer_name.insert(0, config.get('PRINTER', 'windows_printer_name', fallback=''))
        self.entry_printer_name.pack(fill='x', pady=5)
        
        tk.Label(self.frame_windows, text="Deixe em branco para usar impressora padrão", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_secundario'],
                font=('Arial', 9)).pack(anchor='w')
        self.frame_windows.pack(fill='x', pady=5)
        
        # Para COM/ESC_POS
        self.frame_com = tk.Frame(self.campos_impressora_frame, bg=self.cores['fundo_card'])
        tk.Label(self.frame_com, text="Porta:", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario']).pack(side='left', padx=(0, 10))
        
        self.entry_port = tk.Entry(self.frame_com, width=15, font=('Arial', 10))
        self.entry_port.insert(0, config.get('PRINTER', 'port', fallback='COM1'))
        self.entry_port.pack(side='left', padx=(0, 20))
        
        tk.Label(self.frame_com, text="Baudrate:", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario']).pack(side='left', padx=(0, 10))
        
        self.entry_baudrate = tk.Entry(self.frame_com, width=10, font=('Arial', 10))
        self.entry_baudrate.insert(0, config.get('PRINTER', 'baudrate', fallback='9600'))
        self.entry_baudrate.pack(side='left')  # CORRIGIDO
        self.frame_com.pack(fill='x', pady=5)
        
        # Para Ethernet
        self.frame_ethernet = tk.Frame(self.campos_impressora_frame, bg=self.cores['fundo_card'])
        tk.Label(self.frame_ethernet, text="Endereço IP:", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario']).pack(side='left', padx=(0, 10))
        
        self.entry_ip = tk.Entry(self.frame_ethernet, width=20, font=('Arial', 10))
        self.entry_ip.insert(0, config.get('PRINTER', 'ethernet_ip', fallback='192.168.1.100'))
        self.entry_ip.pack(side='left', padx=(0, 20))
        
        tk.Label(self.frame_ethernet, text="Porta:", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario']).pack(side='left', padx=(0, 10))
        
        self.entry_ethernet_port = tk.Entry(self.frame_ethernet, width=10, font=('Arial', 10))
        self.entry_ethernet_port.insert(0, config.get('PRINTER', 'ethernet_port', fallback='9100'))
        self.entry_ethernet_port.pack(side='left')
        self.frame_ethernet.pack(fill='x', pady=5)
        
        # Comportamento
        tk.Label(scrollable_frame, text="Comportamento:", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=(20, 10))
        row += 1
        
        frame_comportamento = tk.Frame(scrollable_frame, bg=self.cores['fundo_card'])
        frame_comportamento.grid(row=row, column=0, columnspan=3, sticky='w', pady=5)
        
        self.var_auto_print = tk.BooleanVar(value=config.getboolean('PRINTER', 'auto_print', True))
        cb_auto = tk.Checkbutton(frame_comportamento, text="Imprimir Automaticamente",
                               variable=self.var_auto_print,
                               bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                               selectcolor=self.cores['fundo_medio'])
        cb_auto.pack(side='left', padx=(0, 20))
        
        self.var_open_drawer = tk.BooleanVar(value=config.getboolean('PRINTER', 'open_drawer', False))
        cb_drawer = tk.Checkbutton(frame_comportamento, text="Abrir Gaveta após venda",
                                 variable=self.var_open_drawer,
                                 bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                                 selectcolor=self.cores['fundo_medio'])
        cb_drawer.pack(side='left', padx=(0, 20))
        
        self.var_paper_cut = tk.BooleanVar(value=config.getboolean('PRINTER', 'paper_cut', True))
        cb_cut = tk.Checkbutton(frame_comportamento, text="Cortar Papel Automaticamente",
                              variable=self.var_paper_cut,
                              bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                              selectcolor=self.cores['fundo_medio'])
        cb_cut.pack(side='left')
        row += 1
        
        # Botões
        frame_botoes = tk.Frame(scrollable_frame, bg=self.cores['fundo_card'])
        frame_botoes.grid(row=row, column=0, columnspan=3, pady=30)
        
        btn_salvar = tk.Button(frame_botoes, text="💾 SALVAR",
                              bg=self.cores['sucesso'], fg='white',
                              font=('Arial', 11, 'bold'),
                              width=12, height=2,
                              command=self.salvar_config_impressora)
        btn_salvar.pack(side='left', padx=10)
        
        btn_testar = tk.Button(frame_botoes, text="🖨️ TESTAR",
                              bg=self.cores['botao_primario'], fg='white',
                              font=('Arial', 11, 'bold'),
                              width=12, height=2,
                              command=self.testar_impressora)
        btn_testar.pack(side='left', padx=10)
        
        btn_fechar = tk.Button(frame_botoes, text="❌ FECHAR",
                              bg=self.cores['erro'], fg='white',
                              font=('Arial', 11, 'bold'),
                              width=12, height=2,
                              command=config_window.destroy)
        btn_fechar.pack(side='left', padx=10)
        
        # Mostrar campos corretos inicialmente
        self._atualizar_campos_impressora()
    
    def _atualizar_campos_impressora(self):
        """Mostrar/ocultar campos baseado no tipo de impressora"""
        tipo = self.var_tipo_impressora.get()
        
        # Esconder todos
        for frame in [self.frame_windows, self.frame_com, self.frame_ethernet]:
            frame.pack_forget()
        
        # Mostrar apenas o necessário
        if tipo == 'windows':
            self.frame_windows.pack(fill='x', pady=5)
        elif tipo in ['esc_pos', 'com']:
            self.frame_com.pack(fill='x', pady=5)
        elif tipo == 'ethernet':
            self.frame_ethernet.pack(fill='x', pady=5)
        
    def salvar_config_impressora(self):
        """Salvar configuração da impressora"""
        try:
            # Salvar no config.ini
            config.set('PRINTER', 'type', self.var_tipo_impressora.get())
            config.set('PRINTER', 'windows_printer_name', self.entry_printer_name.get())
            config.set('PRINTER', 'port', self.entry_port.get())
            config.set('PRINTER', 'baudrate', self.entry_baudrate.get())
            config.set('PRINTER', 'auto_print', 'True' if self.var_auto_print.get() else 'False')
            config.set('PRINTER', 'open_drawer', 'True' if self.var_open_drawer.get() else 'False')
            
            messagebox.showinfo("Sucesso", "Configuração salva com sucesso!")
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar configuração: {e}")
            messagebox.showerror("Erro", f"Erro ao salvar: {e}")
    
    def testar_impressora(self):
        """Testar impressora"""
        try:
            from printer_manager import printer_manager
            printer_manager.print_test_page()
            messagebox.showinfo("Teste", "Página de teste enviada para impressora!")
        except Exception as e:
            self.logger.error(f"Erro no teste impressora: {e}")
            messagebox.showerror("Erro", f"Erro ao testar: {e}")
        
    def atualizar_data_hora(self):
        """Atualizar data e hora em tempo real"""
        agora = dt.now()
        data_hora_str = agora.strftime("%d/%m/%Y %H:%M:%S")
        self.label_data_hora.config(text=data_hora_str)
        self.root.after(1000, self.atualizar_data_hora)
    
    def atualizar_modo(self, novo_modo: str):
        """Atualizar modo de operação com histórico"""
        # Guardar modo atual no histórico
        if hasattr(self, 'modo_atual') and self.modo_atual != novo_modo:
            if not hasattr(self, 'modo_historico'):
                self.modo_historico = []
            
            # Não adicionar modos temporários ao histórico
            modos_temporarios = ['consultar_preco']
            if self.modo_atual not in modos_temporarios:
                self.modo_historico.append(self.modo_atual)
            
            # Limitar histórico a 10 modos
            if len(self.modo_historico) > 10:
                self.modo_historico.pop(0)
        
        # Atualizar modo atual
        self.modo_atual = novo_modo
        modo_info = self.modo_cores.get(novo_modo, self.modo_cores['venda'])
        
        # Atualizar cartão de modo
        if hasattr(self, 'card_modo'):
            self.card_modo.winfo_children()[1].config(
                text=modo_info['name'],
                fg=modo_info['fg']
            )
        
        # Atualizar botões de função
        self.atualizar_botoes_modo()
        
        # Atualizar display
        self.atualizar_display_modo()
        
        self.logger.info(f"Modo alterado para: {novo_modo}")
    
    def atualizar_botoes_modo(self):
        """Atualizar botões de função dinamicamente baseados no modo atual"""
        # Limpar container
        for widget in self.funcoes_container.winfo_children():
            widget.destroy()
        
        # Botões específicos por modo
        if self.modo_atual == 'login':
            # Modo login - apenas funções básicas
            botoes = [
                ('FUNÇÕES', self.cores['botao_primario'], '⚙️', self.modo_funcoes),
                ('CONSULTAR PREÇO', self.cores['sucesso'], '🔍', self.consultar_preco),
                #('TESTE SCANNER', self.cores['alerta'], '📷', self.testar_scanner_rapido)
            ]
        
        elif self.modo_atual == 'venda':
            # Modo venda - todas funções de venda
            botoes = [
                ('FUNÇÕES', self.cores['botao_primario'], '⚙️', self.modo_funcoes),
                ('Usper', self.cores['botao_primario'], '⚙️', self.modo_supervisor),
                ('CONSULTAR PREÇO', self.cores['sucesso'], '🔍', self.consultar_preco),
                ('ANULAR ITEM', self.cores['erro'], '❌', self.anular_item),
                ('CANCELAR VENDA', self.cores['erro'], '🗑️', self.cancelar_venda),
                ('APLICAR PROMOÇÃO', '#9b59b6', '🏷️', self.aplicar_promocao_manual),
                ('TOTAL', self.cores['destaque'], '💰', self.finalizar_venda),
                ('DESCONTO', self.cores['botao_secundario'], '🎯', self.aplicar_desconto),
                ('CLIENTE', self.cores['sucesso'], '👤', self.selecionar_cliente),
                ('BALANÇA', self.cores['alerta'], '⚖️', self.modo_balanca)
            ]
        
        elif self.modo_atual == 'pagamento':
            # Modo pagamento - formas de pagamento dinâmicas
            botoes = []
            
            # Carregar formas de pagamento do banco
            try:
                from database import DatabaseManager
                db = DatabaseManager()
                formas = db.get_active_payment_methods(int(self.pdv_config['loja_id']))
                
                for forma in formas:
                    nome = forma['nome']
                    codigo = forma['codigo']
                    
                    # Mapear cores por código
                    cores_map = {
                        'DIN': '#27ae60',    # Dinheiro - verde
                        'DEB': '#e67e22',    # Débito - laranja
                        'CRE': '#8e44ad',    # Crédito - roxo
                        'TPA': '#3498db',    # TPA - azul
                        'CCL': '#f1c40f',    # Cartão cliente - amarelo
                        'CHE': '#1abc9c',    # Cheque - turquesa
                        'PIX': '#0984e3',    # PIX - azul claro
                        'VLE': '#e84393',    # Vale - rosa
                    }
                    
                    # Mapear ícones
                    icones_map = {
                        'DIN': '💵',
                        'DEB': '💳',
                        'CRE': '💳',
                        'TPA': '📱',
                        'CCL': '👤',
                        'CHE': '🏦',
                        'PIX': '📱',
                        'VLE': '🎫',
                    }
                    
                    cor = cores_map.get(codigo, self.cores['botao_primario'])
                    icone = icones_map.get(codigo, '💰')
                    
                    # Criar botão para esta forma de pagamento
                    botoes.append((nome, cor, icone, 
                                 lambda f=codigo: self.processar_pagamento(f)))
            
            except Exception as e:
                self.logger.error(f"Erro ao carregar formas de pagamento: {e}")
                # Usar formas padrão se houver erro
                botoes_padrao = [
                    ('DINHEIRO', '#27ae60', '💵', lambda: self.processar_pagamento('DIN')),
                    ('CARTÃO DÉBITO', '#e67e22', '💳', lambda: self.processar_pagamento('DEB')),
                    ('CARTÃO CRÉDITO', '#8e44ad', '💳', lambda: self.processar_pagamento('CRE')),
                    ('TPA MÓVEL', '#3498db', '📱', lambda: self.processar_pagamento('TPA')),
                    ('CARTÃO CLIENTE', '#f1c40f', '👤', lambda: self.processar_pagamento('CCL'))
                ]
                botoes.extend(botoes_padrao)
            
            # Botões de controle no modo pagamento
            botoes_controle = [
                ('MULTIPLAS FORMAS', '#9b59b6', '💳💵', self.pagamento_multiplas_formas),
                ('CORRIGIR PAGAMENTO', self.cores['alerta'], '↩️', self.corrigir_pagamento),
                ('CANCELAR VENDA', self.cores['erro'], '❌', self.cancelar_pagamento)
            ]
            botoes.extend(botoes_controle)
        
        elif self.modo_atual == 'funcoes':
            # Modo funções - opções administrativas
            botoes = [
                ('ABRIR CAIXA', '#27ae60', '💰', self.abrir_caixa),  # NOVO
                ('SANGRIA', self.cores['erro'], '💰', self.modo_sangria),
                ('SANGRIAR', self.cores['erro'], '💰', self.modo_sangria),
                ('DEVOLUÇÃO', self.cores['alerta'], '🔄', self.modo_devolucao),
                ('FECHAR CAIXA', '#16a085', '🔒', self.fechar_caixa),
                ('ABRIR GAVETA', self.cores['botao_secundario'], '🗄️', self.abrir_gaveta),
                ('TESTE IMPRESSORA', '#7f8c8d', '🖨️', self.teste_impressora),
                ('RELATÓRIO DIÁRIO', '#c0392b', '📊', self.relatorio_diario),
                ('CONFIGURAÇÕES', '#3498db', '⚙️', self.abrir_configuracoes),
                ('VOLTAR', self.cores['fundo_card'], '↩️', self.voltar_modo_venda)
            ]
        
        elif self.modo_atual == 'supervisor_ativo':
            # Modo supervisor ativo - funções especiais
            botoes = [
                ('ABRIR CAIXA', '#27ae60', '💰', self.abrir_caixa),  # NOVO
                ('SANGRIA', self.cores['erro'], '💰', self.modo_sangria),
                ('SANGRIAR', self.cores['erro'], '💰', self.modo_sangria),
                ('DEVOLUÇÃO', self.cores['alerta'], '🔄', self.modo_devolucao),
                ('FECHAR CAIXA', '#16a085', '🔒', self.fechar_caixa),
                ('ABRIR GAVETA', self.cores['botao_secundario'], '🗄️', self.abrir_gaveta),
                ('TESTE IMPRESSORA', '#7f8c8d', '🖨️', self.teste_impressora),
                ('RELATÓRIO DIÁRIO', '#c0392b', '📊', self.relatorio_diario),
                ('CONFIGURAÇÕES', '#3498db', '⚙️', self.abrir_configuracoes),
                ('VOLTAR', self.cores['fundo_card'], '↩️', self.voltar_modo_venda)
               
            ]
        
        elif self.modo_atual == 'sangria':
            # Modo sangria
            botoes = [
                ('DINHEIRO', '#27ae60', '💵', lambda: self.processar_sangria('DIN')),
                ('CARTÃO DÉBITO', '#e67e22', '💳', lambda: self.processar_sangria('DEB')),
                ('CARTÃO CRÉDITO', '#8e44ad', '💳', lambda: self.processar_sangria('CRE')),
                ('TPA MÓVEL', '#3498db', '📱', lambda: self.processar_sangria('TPA')),
                ('TERMINAR SANGRIA', self.cores['sucesso'], '✓', self.terminar_sangria),
                ('CANCELAR SANGRIA', self.cores['erro'], '❌', self.cancelar_sangria),
                ('VOLTAR', self.cores['fundo_card'], '↩️', self.voltar_modo_funcoes)
            ]


        elif self.modo_atual == 'sangria_avancada':
            # Modo sangria avançada - botões dinâmicos
            botoes = []
            
            self.logger.info(f"=== CRIANDO BOTÕES SANGRIA ===")
            self.logger.info(f"Tem sangria_formas: {hasattr(self, 'sangria_formas')}")
            
            if hasattr(self, 'sangria_formas') and self.sangria_formas:
                formas_disponiveis = [f for f in self.sangria_formas if f.get('valor_disponivel', 0) > 0]
                self.logger.info(f"Formas disponíveis: {len(formas_disponiveis)}")
                
                # Mostrar máximo 6 formas na primeira linha
                for i, forma in enumerate(formas_disponiveis[:6]):
                    nome = forma['nome'][:10] if len(forma['nome']) > 10 else forma['nome']
                    codigo = forma['codigo']
                    disponivel = forma.get('valor_disponivel', 0)
                    
                    self.logger.info(f"Criando botão {i+1}: {nome} ({codigo}) - {disponivel}")
                    
                    # Definir cor baseada no código
                    cores_map = {
                        'DIN': '#27ae60',    # Verde
                        'MC': '#e67e22',     # Laranja (Multicaixa)
                        'CC': '#8e44ad',     # Roxo (Cartão Crédito)
                        'CD': '#3498db',     # Azul (Cartão Débito)
                        'CL': '#f1c40f'      # Amarelo (Cartão Cliente)
                    }
                    
                    cor = cores_map.get(codigo, self.cores['botao_primario'])
                    
                    # Texto do botão (2 linhas)
                    texto_botao = f"{nome}\n{self.formatar_moeda(disponivel, False)}"
                    
                    botoes.append((
                        texto_botao,
                        cor,
                        '💰',
                        lambda c=codigo: self.processar_sangria_forma(c)
                    ))
                
                # Se houver mais formas, adicionar na segunda linha
                if len(formas_disponiveis) > 6:
                    for i, forma in enumerate(formas_disponiveis[6:12], start=6):
                        nome = forma['nome'][:8] if len(forma['nome']) > 8 else forma['nome']
                        codigo = forma['codigo']
                        disponivel = forma.get('valor_disponivel', 0)
                        
                        self.logger.info(f"Criando botão linha 2: {nome} ({codigo})")
                        
                        cor = self.cores['botao_secundario']
                        texto_botao = f"{nome}\n{self.formatar_moeda(disponivel, False)}"
                        
                        botoes.append((
                            texto_botao,
                            cor,
                            '💰',
                            lambda c=codigo: self.processar_sangria_forma(c)
                        ))
            
            else:
                self.logger.warning("Nenhuma forma disponível para botões")
                # Botão de informação
                botoes.append((
                    "SEM VALORES",
                    self.cores['texto_secundario'],
                    '⚠️',
                    lambda: None
                ))
            
            # Botões de controle (sempre aparecem)
            botoes_controle = [
                ('✓ TERMINAR', self.cores['sucesso'], '✓', self.terminar_sangria),
                ('✗ CANCELAR', self.cores['erro'], '✗', self.cancelar_sangria),
                ('↩ VOLTAR', self.cores['fundo_card'], '↩', self.cancelar_sangria)
            ]
            
            botoes.extend(botoes_controle)
            self.logger.info(f"Total botões criados: {len(botoes)}")
                
        
        
        elif self.modo_atual == 'devolucao':
            # Modo devolução
            botoes = [
                ('DEVOLUÇÃO PARCIAL', self.cores['alerta'], '🔄', self.devolucao_parcial),
                ('DEVOLUÇÃO TOTAL', self.cores['erro'], '🔄', self.devolucao_total),
                ('CONSULTAR DOCUMENTO', self.cores['sucesso'], '🔍', self.consultar_documento),
                ('TERMINAR DEVOLUÇÃO', self.cores['sucesso'], '✓', self.terminar_devolucao),
                ('CANCELAR DEVOLUÇÃO', self.cores['erro'], '❌', self.cancelar_devolucao),
                ('VOLTAR', self.cores['fundo_card'], '↩️', self.voltar_modo_funcoes)
            ]
        
        elif self.modo_atual == 'consultar_preco':
            # Modo consulta de preço
            botoes = [
                ('CONSULTAR', self.cores['sucesso'], '🔍', self.consultar_preco_buffer),
                #('SCANNER TESTE', self.cores['alerta'], '📷', self.testar_scanner_rapido),
                ('VOLTAR', self.cores['fundo_card'], '↩️', self.voltar_modo_anterior)
            ]
        
        else:
            # Modo desconhecido - botões padrão
            botoes = [
                ('VOLTAR', self.cores['fundo_card'], '↩️', lambda: self.atualizar_modo('venda')),
                ('FUNÇÕES', self.cores['botao_primario'], '⚙️', self.modo_funcoes)
            ]
        
        # Criar botões no container
        for texto, cor, icone, comando in botoes:
            self._criar_botao_funcao(texto, cor, icone, comando)
        
        # Atualizar o canvas para ajustar o scroll
        self.root.after(100, self._atualizar_scroll_funcoes)
            
    def atualizar_display_modo(self):
        """Atualizar mensagem do display baseado no modo"""
        mensagens_modo = {
            'login': ["MODO LOGIN", "DIGITE NÚMERO DO TRABALHADOR (4 dígitos)", "ENTER para confirmar"],
            'venda': ["MODO VENDA", "DIGITE CÓDIGO DO PRODUTO", "QTS para quantidade"],
            'pagamento': ["MODO PAGAMENTO", "SELECIONE FORMA DE PAGAMENTO", "TOTAL: Kz 0,00"],
            'funcoes': ["MODO FUNÇÕES", "SELECIONE UMA OPÇÃO", ""],
            'sangria': ["MODO SANGRIA", "DIGITE VALOR DA SANGRIA", "SELECIONE FORMA DE PAGAMENTO"],
            'devolucao': ["MODO DEVOLUÇÃO", "DIGITE NÚMERO DO DOCUMENTO", "ENTER para confirmar"]
        }
        
        mensagem = mensagens_modo.get(self.modo_atual, ["", "", ""])
        self.display_lines = mensagem
        self.atualizar_display()
    
    def atualizar_display(self):
        """Atualizar conteúdo do display"""
        for i, line in enumerate(self.display_lines):
            label = getattr(self, f'display_line{i+1}')
            label.config(text=line)
    
    def set_display_message(self, line1="", line2="", line3=""):
        """Definir mensagem específica no display"""
        self.display_lines = [line1, line2, line3]
        self.atualizar_display()
    
    def tecla_pressionada(self, tecla: str):
        """Processar tecla pressionada no teclado numérico"""
        if tecla in '0123456789':
            self.input_buffer += tecla
            self.atualizar_buffer_display()
            
        elif tecla == ',':
            if ',' not in self.input_buffer:
                self.input_buffer += ','
                self.atualizar_buffer_display()
        
        elif tecla == '00':
            self.input_buffer += '00'
            self.atualizar_buffer_display()
        
        elif tecla == 'Apagar':
            self.input_buffer = self.input_buffer[:-1]
            self.atualizar_buffer_display()
        
        elif tecla == 'Qts':
            self.processar_quantidade()
        
        elif tecla == 'Cancelar':
            self.cancelar_operacao()
        
        elif tecla == 'Enter':
            # Verificar se está aguardando valor pago
            if hasattr(self, 'aguardando_valor_pago') and self.aguardando_valor_pago:
                self.processar_valor_pago()
            else:
                self.processar_enter()
        
        self.logger.debug(f"Tecla pressionada: {tecla}, Buffer: {self.input_buffer}")
    
    def atualizar_buffer_display(self):
        """Atualizar display com buffer atual"""
        if self.modo_atual == 'login':
            # Verificar se estamos digitando senha ou worker ID
            if hasattr(self, 'login_worker_id') and self.login_worker_id:
                # Modo senha - mostrar asteriscos
                display_text = '*' * len(self.input_buffer)
                self.set_display_message(
                    "MODO LOGIN",
                    f"TRABALHADOR: {self.login_worker_id}",
                    f"SENHA: {display_text}"
                )
            else:
                # Modo worker ID - mostrar normalmente
                display_text = self.input_buffer
                self.set_display_message(
                    "MODO LOGIN",
                    f"NÚMERO TRABALHADOR: {display_text}",
                    "ENTER para confirmar"
                )
        else:
            self.set_display_message(
                f"MODO {self.modo_atual.upper()}",
                f"> {self.input_buffer}",
                ""
            )
    
    def processar_quantidade(self):
        """Processar botão Qts (quantidade)"""
        if self.modo_atual == 'venda':
            if self.input_buffer:
                try:
                    quantidade = float(self.input_buffer.replace(',', '.'))
                    if quantidade > 0:
                        self.quantidade_pendente = quantidade
                        self.set_display_message(
                            "MODO VENDA",
                            f"QUANTIDADE: {quantidade}",
                            "DIGITE CÓDIGO DO PRODUTO"
                        )
                        self.input_buffer = ""
                    else:
                        self.set_display_message(
                            "ERRO",
                            "QUANTIDADE INVÁLIDA",
                            "DIGITE VALOR > 0"
                        )
                except ValueError:
                    self.set_display_message(
                        "ERRO",
                        "QUANTIDADE INVÁLIDA",
                        "DIGITE VALOR NUMÉRICO"
                    )
            else:
                # Sem quantidade específica, usar 1
                self.quantidade_pendente = 1
                self.set_display_message(
                    "MODO VENDA",
                    "QUANTIDADE: 1",
                    "DIGITE CÓDIGO DO PRODUTO"
                )

    def processar_enter(self):
        """Processar botão Enter"""
        self.logger.info(f"ENTER pressionado. Buffer atual: '{self.input_buffer}'")
        self.logger.info(f"Modo atual: {self.modo_atual}")
        
        if not self.input_buffer:
            self.logger.warning("Buffer vazio ao pressionar ENTER")
            return
        
        if self.modo_atual == 'login':
            self.logger.info("Chamando processar_login...")
            self.processar_login()
        
        elif self.modo_atual == 'venda':
            self.adicionar_produto()  # ESTE É O PROBLEMA! Deve ser apenas para modo venda
        
        elif self.modo_atual == 'consultar_preco':
            self.consultar_preco_buffer()
        
        elif self.modo_atual == 'desconto':  # ADICIONAR ESTE
            self.processar_desconto(self.input_buffer)
            self.input_buffer = ""
            return
        
        elif self.modo_atual == 'supervisor_login':
            self.processar_supervisor_login()
        
        elif self.modo_atual == 'sangria_avancada' and hasattr(self, 'modo_sangria_digitar') and self.modo_sangria_digitar:
            self.processar_valor_sangria()
            return
        
        # Se chegou aqui sem match, limpar buffer
        self.input_buffer = ""
        self.logger.info("Buffer limpo após processamento")

    def processar_login(self):
        """Processar tentativa de login"""
        worker_id = self.input_buffer
        
        self.logger.info(f"Processar login - Buffer: '{self.input_buffer}'")
        
        # Se já temos worker_id, agora pedir senha
        if hasattr(self, 'login_worker_id') and self.login_worker_id:
            # Processar senha
            senha = self.input_buffer
            
            self.logger.info(f"Processando senha para worker {self.login_worker_id}: {senha}")
            
            # Validação básica da senha
            if len(senha) != 5 or not senha.isdigit():
                self.set_display_message(
                    "ERRO",
                    "SENHA INVÁLIDA",
                    "DEVE TER 5 DÍGITOS"
                )
                self.input_buffer = ""
                return
            
            # Tentar fazer login
            self.logger.info(f"Chamando auth_manager.validate_credentials...")
            sucesso, usuario = auth_manager.validate_credentials(
                self.login_worker_id, senha
            )
            
            self.logger.info(f"Resultado login: Sucesso={sucesso}, Usuário={usuario}")
            
            if sucesso and usuario:
                # Criar sessão
                session_id = auth_manager.create_session(usuario)
                self.sessao_atual = session_id
                self.usuario_atual = usuario
                
                # Atualizar interface
                self.atualizar_modo('venda')
                
                # Atualizar informações do operador no rodapé
                if len(self.info_widgets) > 2:
                    self.info_widgets[2].config(
                        text=f"{usuario['numero_trabalhador']} - {usuario['nome']}"
                    )
                
                # Mensagem de boas-vindas
                self.set_display_message(
                    "LOGIN BEM-SUCEDIDO",
                    f"BEM-VINDO, {usuario['nome']}",
                    f"MODO: {usuario['perfil'].upper()}"
                )
                
                self.logger.info(f"Usuário {usuario['nome']} logado com sucesso. Sessão: {session_id}")
                
            else:
                # Login falhou
                self.set_display_message(
                    "ERRO DE LOGIN",
                    "CREDENCIAIS INVÁLIDAS",
                    "TENTE NOVAMENTE"
                )
                self.logger.warning(f"Login falhou para worker {self.login_worker_id}")
            
            # Limpar estado de login
            delattr(self, 'login_worker_id')
            self.input_buffer = ""
            
        else:
            # Primeira etapa: validar e guardar worker_id
            
            if len(worker_id) != 4 or not worker_id.isdigit():
                self.set_display_message(
                    "ERRO",
                    "NÚMERO TRABALHADOR INVÁLIDO",
                    "DEVE TER 4 DÍGITOS"
                )
                self.input_buffer = ""
                return
            
            self.login_worker_id = worker_id
            self.logger.info(f"Worker ID armazenado: {self.login_worker_id}")
            
            self.set_display_message(
                "LOGIN",
                f"TRABALHADOR: {worker_id}",
                "DIGITE SENHA (5 dígitos)"
            )
            self.input_buffer = ""
    
    def adicionar_produto(self):
        """Adicionar produto ao carrinho"""
        if not self.conexao_status:
            self.set_display_message(
                "ERRO",
                "SEM CONEXÃO",
                "NÃO É POSSÍVEL ADICIONAR PRODUTO"
            )
            return
        
        codigo = self.input_buffer.strip()
        
        # Consultar produto no cache/banco
        produto = self.consultar_produto_no_cache(codigo)
        
        if not produto:
            self.set_display_message(
                "ERRO",
                "PRODUTO NÃO ENCONTRADO",
                f"CÓDIGO: {codigo}"
            )
            return
        
        # Usar quantidade pendente ou padrão 1
        quantidade = self.quantidade_pendente if self.quantidade_pendente else 1
        
        # Converter preco_unitario para float se for Decimal
        preco_unitario = produto['preco_venda']
        if hasattr(preco_unitario, 'to_eng_string'):  # É Decimal
            preco_unitario = float(preco_unitario)
        
        # Calcular total
        total = preco_unitario * quantidade
        
        # VERIFICAR SE PRODUTO JÁ EXISTE NO CARRINHO
        produto_existente = None
        for item in self.carrinho:
            if item['produto_id'] == produto['id'] and item['preco_unitario'] == preco_unitario:
                produto_existente = item
                break
        
        if produto_existente:
            # ATUALIZAR PRODUTO EXISTENTE
            produto_existente['quantidade'] += quantidade
            produto_existente['total'] += total
            
            # Mensagem de atualização
            self.set_display_message(
                "PRODUTO ATUALIZADO",
                f"{produto['descricao'][:30]}",
                f"QTD: {produto_existente['quantidade']} TOTAL: {self.formatar_moeda(produto_existente['total'])}"
            )
        else:
            # ADICIONAR NOVO PRODUTO
            item = {
                'produto_id': produto['id'],
                'codigo': produto['codigo'],
                'descricao': produto['descricao'],
                'quantidade': quantidade,
                'preco_unitario': preco_unitario,
                'total': total,
                'taxa_id': produto['taxa_id'],
                'taxa_percentagem': float(produto.get('taxa_percentagem', 0)),
                'categoria': produto.get('categoria', ''),
                'unidade_medida': produto.get('unidade_medida', 'UN')
            }
            
            self.carrinho.append(item)
            
            # Mensagem de confirmação
            self.set_display_message(
                "PRODUTO ADICIONADO",
                f"{produto['descricao'][:30]}",
                f"QTD: {quantidade} TOTAL: {self.formatar_moeda(total)}"
            )
        
        # Atualizar Treeview
        self.atualizar_lista_produtos()
        
        # Atualizar totais
        self.atualizar_totais()
        
        # Limpar quantidade pendente
        self.quantidade_pendente = None
        self.input_buffer = ""
    
    def consultar_produto_no_cache(self, codigo: str) -> Optional[Dict]:
        """Consultar produto no cache ou banco"""
        # Primeiro tenta no cache
        produto = product_cache.get(codigo)
        
        if produto:
            return produto
        
        # Se não tem no cache, busca no banco
        try:
            from database import DatabaseManager
            db = DatabaseManager(connection_pool)
            produto = db.get_product_by_code(codigo)
            
            if produto:
                # Armazena no cache
                product_cache.set(codigo, produto)
                return produto
        
        except Exception as e:
            self.logger.error(f"Erro ao consultar produto: {e}")
        
        return None
    
    def atualizar_lista_produtos(self):
        """Atualizar Treeview com produtos do carrinho"""
        # Limpar Treeview
        for item in self.tree_produtos.get_children():
            self.tree_produtos.delete(item)
        
        # Adicionar itens
        for i, item in enumerate(self.carrinho, 1):
            valores = (
                i,
                item['codigo'],
                item['descricao'][:40],
                f"{item['quantidade']:.3f}".rstrip('0').rstrip('.'),
                self.formatar_moeda(item['preco_unitario']),
                self.formatar_moeda(item['total']),
                f"{item['taxa_percentagem']:.1f}%"
            )
            self.tree_produtos.insert('', 'end', values=valores)
    
    def atualizar_totais(self):
        """Atualizar totais da venda"""
        total_itens = len(self.carrinho)
        total_geral = 0
        
        for item in self.carrinho:
            total = self._convert_decimal(item['total'])
            if hasattr(total, 'to_eng_string'):  # É Decimal
                total_geral += float(total)
            else:
                total_geral += total
        
        # Atualizar cartões
        self.card_artigos.winfo_children()[1].config(text=str(total_itens))
        self.card_total.winfo_children()[1].config(text=self.formatar_moeda(total_geral))
        
        # Guardar total para pagamento
        self.modo_pagamento_total = total_geral

    def formatar_moeda(self, valor: float, show_symbol: bool = True) -> str:
        """Formatar valor como moeda - VERSÃO CORRIGIDA"""
        try:
            # Converter para float se necessário
            if isinstance(valor, str):
                valor = float(valor.replace(',', '.'))
            
            # Se é Decimal, converter para float
            if hasattr(valor, 'to_eng_string'):
                valor = float(valor)
            
            # Obter configurações
            symbol = config.get('CURRENCY', 'symbol', fallback='Kz')
            
            # Formatar com separadores portugueses
            formatted = f"{valor:,.2f}"
            formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
            
            # Adicionar símbolo
            if show_symbol:
                return f"{symbol} {formatted}"
            else:
                return formatted
                
        except Exception as e:
            self.logger.error(f"Erro ao formatar moeda {valor}: {e}")
            # Fallback simples
            return f"Kz {valor:,.2f}"
        
    def consultar_preco(self):
        """Mudar para modo consulta de preço"""
        self.set_display_message(
            "CONSULTAR PREÇO",
            "DIGITE CÓDIGO DO PRODUTO",
            "ENTER para consultar"
        )
        self.modo_anterior = self.modo_atual
        self.modo_atual = 'consultar_preco'
    
    def consultar_preco_buffer(self):
        """Consultar preço do produto no buffer"""
        codigo = self.input_buffer.strip()
        
        produto = self.consultar_produto_no_cache(codigo)
        
        if produto:
            self.set_display_message(
                "CONSULTA DE PREÇO",
                f"{produto['descricao'][:30]}",
                f"PREÇO: {self.formatar_moeda(produto['preco_venda'])}"
            )
        else:
            self.set_display_message(
                "PRODUTO NÃO ENCONTRADO",
                f"CÓDIGO: {codigo}",
                ""
            )
    
    def modo_funcoes(self):
        """Mudar para modo funções"""
        self.atualizar_modo('funcoes')
    
    def modo_pagamento(self):
        """Mudar para modo pagamento"""
        if not self.carrinho:
            self.set_display_message(
                "ERRO",
                "CARRINHO VAZIO",
                "ADICIONE PRODUTOS PRIMEIRO"
            )
            return
        
        # Calcular total
        total = sum(item['total'] for item in self.carrinho)
        self.modo_pagamento_total = total
        
        self.atualizar_modo('pagamento')
        
        # Mostrar total
        self.set_display_message(
            "MODO PAGAMENTO",
            f"TOTAL: {self.formatar_moeda(total)}",
            "SELECIONE FORMA DE PAGAMENTO"
        )
    
    def finalizar_venda(self):
        """Finalizar venda atual"""
        if not self.carrinho:
            self.set_display_message(
                "ERRO",
                "CARRINHO VAZIO",
                "ADICIONE PRODUTOS PRIMEIRO"
            )
            return
        
        # Calcular totais
        total_venda = sum(item['total'] for item in self.carrinho)
        
        # Ir para modo pagamento
        self.modo_pagamento_total = total_venda
        self.atualizar_modo('pagamento')
        
        # Mostrar total no display
        self.set_display_message(
            "MODO PAGAMENTO",
            f"TOTAL: {self.formatar_moeda(total_venda)}",
            "SELECIONE FORMA DE PAGAMENTO"
        )
    
    def processar_pagamento(self, forma_pagamento: str):
        """Processar pagamento com forma específica"""
        self.forma_pagamento_atual = forma_pagamento
        
        if forma_pagamento == 'DIN':
            # Para dinheiro, pedir valor pago
            self.set_display_message(
                "PAGAMENTO EM DINHEIRO",
                f"TOTAL: {self.formatar_moeda(self.modo_pagamento_total)}",
                "DIGITE VALOR PAGO"
            )
            self.aguardando_valor_pago = True
            
        else:
            # Para outras formas, usar valor exato
            # Converter para float se for Decimal
            total = self.modo_pagamento_total
            if hasattr(total, 'to_eng_string'):
                total = float(total)
            
            self.valor_pago = total
            self.troco = 0
            self.finalizar_pagamento()
    
    def _convert_decimal(self, value):
        """Converter Decimal para float se necessário"""
        if value is None:
            return 0.0
        elif hasattr(value, 'to_eng_string'):  # É Decimal
            return float(value)
        return value
    
    def processar_valor_pago(self):
        """Processar valor pago digitado"""
        if not self.input_buffer:
            return
        
        try:
            # Converter valor
            valor_str = self.input_buffer.replace(',', '.')
            valor_pago = float(valor_str)
            
            # Converter total para float se for Decimal
            total_venda = self._convert_decimal(self.modo_pagamento_total)
            if hasattr(total_venda, 'to_eng_string'):  # É Decimal
                total_venda = float(total_venda)
            
            if valor_pago < total_venda:
                self.set_display_message(
                    "ERRO",
                    "VALOR INSUFICIENTE",
                    f"FALTAM: {self.formatar_moeda(total_venda - valor_pago)}"
                )
                return
            
            self.valor_pago = valor_pago
            self.troco = valor_pago - total_venda
            
            # Finalizar pagamento
            self.finalizar_pagamento()
            
        except ValueError:
            self.set_display_message(
                "ERRO",
                "VALOR INVÁLIDO",
                "DIGITE VALOR NUMÉRICO"
            )
    
    def finalizar_pagamento(self):
        """Finalizar processo de pagamento e emitir documento"""
        try:
            # Obter dados do usuário atual
            user_info = auth_manager.get_user_info(self.sessao_atual)
            if not user_info:
                raise Exception("Sessão inválida")
            
            # Obter cliente atual (selecionado ou padrão)
            if hasattr(self, 'cliente_atual'):
                cliente_nif = self.cliente_atual.get('nif', '000000008')
                cliente_nome = self.cliente_atual.get('nome', 'CONSUMIDOR FINAL')
                cliente_id = self.cliente_atual.get('id', 1)
            else:
                cliente_nif = '000000005'
                cliente_nome = 'CONSUMIDOR FINAL'
                cliente_id = 1
            
            # Obter informações do documento AUTOMATICAMENTE
            loja_id = int(self.pdv_config['loja_id'])
            pdv_id = int(self.pdv_config['pdv_id'])
            total_venda = float(self.modo_pagamento_total)
            
            try:
                # Gerar informações do documento
                doc_info = document_manager.generate_document_info(
                    loja_id, pdv_id, total_venda, cliente_nif
                )
                
                self.logger.info(f"Documento gerado: {doc_info['tipo']} - {doc_info['descricao']}")
                
            except ValueError as e:
                # Cliente precisa de NIF para valor alto
                self.logger.warning(f"Documento não pode ser emitido: {e}")
                
                # Perguntar se quer usar consumidor final
                resposta = messagebox.askyesno(
                    "Documento Requer NIF",
                    f"Valor: {self.formatar_moeda(total_venda)}\n\n"
                    f"Para emitir documento fiscal, é necessário NIF do cliente.\n"
                    f"Deseja usar CONSUMIDOR FINAL e emitir Factura Simplificada?"
                )
                
                if resposta:
                    # Usar consumidor final
                    cliente_nif = '000000076'
                    cliente_nome = 'CONSUMIDOR FINAL'
                    cliente_id = 1
                    
                    # Forçar FS
                    ano = datetime.now().year
                    seq_info = document_manager.get_next_sequence(loja_id, pdv_id, 'FS', ano)
                    
                    doc_info = {
                        'tipo': 'FS',
                        'descricao': 'Factura Simplificada',
                        'numero_venda': seq_info['numero_venda'],
                        'numero_documento': seq_info['numero_documento'],
                        'requires_nif': False,
                        'copies': 1,
                        'sequencia': seq_info['sequencia'],
                        'ano': ano
                    }
                else:
                    # Cancelar venda
                    self.set_display_message(
                        "VENDA CANCELADA",
                        "NIF DO CLIENTE OBRIGATÓRIO",
                        ""
                    )
                    return

            # Preparar dados da venda
            itens_processados = []
            for item in self.carrinho:
                item_processado = item.copy()
                # Converter valores Decimal para float
                for key in ['preco_unitario', 'total', 'taxa_percentagem']:
                    if key in item_processado and hasattr(item_processado[key], 'to_eng_string'):
                        item_processado[key] = float(item_processado[key])
                # Adicionar informações de promoção se existirem
                if 'desconto_promocao' in item:
                    item_processado['promocao_id'] = item['desconto_promocao']
                    item_processado['desconto_promocao_valor'] = item.get('desconto_valor', 0)        
                itens_processados.append(item_processado)
            
                # ... código anterior ...
            
            from datetime import datetime  # Certifique-se que está importado
            
            # Formatar data para MySQL (YYYY-mm-dd HH:MM:SS)
            data_emissao_mysql = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            data_emissao_display = datetime.now().strftime('%d/%m/%Y %H:%M')
            
            sale_data = {
                'empresa_id': int(self.pdv_config['empresa_id']),
                'loja_id': loja_id,
                'pdv_id': pdv_id,
                'usuario_id': self.usuario_atual['id'],
                'cliente_id': cliente_id,  # Usar o cliente_id correto
                'numero_venda': doc_info['numero_venda'],
                'tipo': doc_info['tipo'],
                'numero_documento': doc_info['numero_documento'],
                'ano': doc_info['ano'],
                'itens': itens_processados,
                'total_venda': total_venda,
                'total_pago': float(self.valor_pago),
                'troco': float(self.troco),
                'forma_pagamento': self.forma_pagamento_atual.upper(),
                'operador_nome': user_info['name'],
                'cliente_nome': cliente_nome,
                'cliente_nif': cliente_nif,
                'data_emissao': data_emissao_mysql,  # Formato MySQL
                'data_emissao_display': data_emissao_display,  # Formato display
                'system_entry_date': data_emissao_mysql,  # Igual a data_emissao
                'source_id': self.usuario_atual['id'],
                'document_description': doc_info['descricao'],
                'copies': doc_info['copies'],
                # Adicionar informações da sessão
                'sessao_id': self.sessao_atual,  # ID da sessão
                'valor_iva': 0,  # Será calculado
                'total_sem_iva': total_venda,  # Assumindo sem IVA por enquanto
                'total_iva': 0,
                'total_com_iva': total_venda,
                'taxa_id': 1  # Taxa padrão
            }
            
            # Adicionar promoções aplicadas se existirem
            if hasattr(self, 'promocoes_aplicadas') and self.promocoes_aplicadas:
                sale_data['promocoes_aplicadas'] = self.promocoes_aplicadas
            
            # Calcular resumo IVA
            if config.getboolean('DOCUMENT', 'print_iva_summary', True):
                iva_summary = receipt_generator.calculate_iva_summary(itens_processados)
                sale_data['iva_summary'] = iva_summary
                
                # Calcular totais IVA
                if iva_summary:
                    total_iva = sum(v['valor_iva'] for v in iva_summary.values())
                    total_sem_iva = sum(v['base_sem_iva'] for v in iva_summary.values())
                    sale_data['total_iva'] = total_iva
                    sale_data['total_sem_iva'] = total_sem_iva
            
            # Salvar no banco de dados
            from database import DatabaseManager
            db = DatabaseManager()
            
            self.logger.info(f"=== DADOS DA VENDA ===")
            self.logger.info(f"Data emissão: {sale_data['data_emissao']}")
            self.logger.info(f"Forma pagamento: {sale_data['forma_pagamento']}")
            self.logger.info(f"Total venda: {sale_data['total_venda']}")
            self.logger.info(f"Total pago: {sale_data['total_pago']}")
            
            sucesso, venda_id, mensagem = db.create_sale(sale_data)
            
            if sucesso:
                # Adicionar ID da venda
                sale_data['id'] = venda_id
                
                # Mostrar mensagem de sucesso
                self.set_display_message(
                    "VENDA CONCLUÍDA",
                    f"{doc_info['descricao'].upper()}",
                    f"DOC: {doc_info['numero_documento']}"
                )
                
                # Imprimir recibo (se configurado)
                if config.getboolean('PRINTER', 'auto_print', True):
                    printer_manager.print_receipt(sale_data)
                
                # Salvar recibo em arquivo
                receipt_generator.save_receipt(sale_data)
                
                # Limpar carrinho
                self.carrinho.clear()
                self.atualizar_lista_produtos()
                self.atualizar_totais()
                
                # Limpar atributos de pagamento
                for attr in ['aguardando_valor_pago', 'forma_pagamento_atual', 
                            'modo_pagamento_total', 'valor_pago', 'troco']:
                    if hasattr(self, attr):
                        delattr(self, attr)
                
                # Voltar para modo venda após 3 segundos
                self.root.after(3000, lambda: self.atualizar_modo('venda'))
                
                self.logger.info(f"Venda concluída: {doc_info['numero_documento']} - {doc_info['descricao']}")
                
            else:
                self.set_display_message(
                    "ERRO",
                    "FALHA AO SALVAR VENDA",
                    mensagem[:30]
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao finalizar pagamento: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            self.set_display_message(
                "ERRO NO PAGAMENTO",
                "CONTATE O ADMINISTRADOR",
                str(e)[:30]
            )
        
    def cancelar_operacao(self):
        """Cancelar operação atual"""
        self.input_buffer = ""
        self.quantidade_pendente = None
        
        # Se estiver no meio do login, cancelar tudo
        if hasattr(self, 'login_worker_id'):
            delattr(self, 'login_worker_id')
        
        if self.modo_atual == 'consultar_preco':
            self.atualizar_modo(self.modo_anterior)
        else:
            self.atualizar_display_modo()
    
    def selecionar_cliente(self):
        """Selecionar cliente para a venda"""
        # Verificar se está configurado para pedir cliente
        if not config.getboolean('CLIENT', 'show_client_selection', True):
            # Usar cliente padrão
            self.cliente_atual = {
                'id': 1,
                'nif': '958321456',
                'nome': 'CONSUMIDOR FINAL',
                'tipo': 'Consumidor Final'
            }
            self.card_cliente.winfo_children()[1].config(text="CONSUMIDOR FINAL")
            return
        
        # Criar janela de seleção de cliente
        self.janela_cliente = tk.Toplevel(self.root)
        self.janela_cliente.title("Selecionar Cliente")
        self.janela_cliente.geometry("500x400")
        self.janela_cliente.configure(bg=self.cores['fundo_medio'])
        self.janela_cliente.transient(self.root)
        self.janela_cliente.grab_set()
        
        # Frame de busca
        frame_busca = tk.Frame(self.janela_cliente, bg=self.cores['fundo_medio'])
        frame_busca.pack(fill='x', padx=10, pady=10)
        
        tk.Label(frame_busca, text="Buscar Cliente:", 
                bg=self.cores['fundo_medio'], fg=self.cores['texto_primario'],
                font=('Arial', 11, 'bold')).pack(anchor='w')
        
        # Campo de busca
        frame_input = tk.Frame(frame_busca, bg=self.cores['fundo_medio'])
        frame_input.pack(fill='x', pady=5)
        
        tk.Label(frame_input, text="NIF:", 
                bg=self.cores['fundo_medio'], fg=self.cores['texto_secundario']).pack(side='left')
        
        self.entry_nif_cliente = tk.Entry(frame_input, width=20, font=('Arial', 12))
        self.entry_nif_cliente.pack(side='left', padx=5)
        self.entry_nif_cliente.focus_set()
        
        btn_buscar = tk.Button(frame_input, text="🔍 Buscar",
                              bg=self.cores['botao_primario'], fg='white',
                              command=self.buscar_cliente)
        btn_buscar.pack(side='left', padx=5)
        
        # Botão consumidor final
        btn_consumidor = tk.Button(frame_busca, text="👤 CONSUMIDOR FINAL",
                                  bg=self.cores['sucesso'], fg='white',
                                  font=('Arial', 10, 'bold'),
                                  command=lambda: self.selecionar_cliente_padrao())
        btn_consumidor.pack(fill='x', pady=5)
        
        # Lista de clientes
        frame_lista = tk.Frame(self.janela_cliente, bg=self.cores['fundo_medio'])
        frame_lista.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Treeview para clientes
        columns = ('nif', 'nome', 'telefone')
        self.tree_clientes = ttk.Treeview(frame_lista, columns=columns, 
                                          show='headings', height=10)
        
        self.tree_clientes.heading('nif', text='NIF')
        self.tree_clientes.heading('nome', text='Nome')
        self.tree_clientes.heading('telefone', text='Telefone')
        
        self.tree_clientes.column('nif', width=120)
        self.tree_clientes.column('nome', width=250)
        self.tree_clientes.column('telefone', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_lista, orient='vertical', 
                                 command=self.tree_clientes.yview)
        self.tree_clientes.configure(yscrollcommand=scrollbar.set)
        
        self.tree_clientes.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind duplo clique para selecionar
        self.tree_clientes.bind('<Double-1>', self.selecionar_cliente_da_lista)
        
        # Carregar clientes
        self.carregar_clientes()
    
    def carregar_clientes(self):
        """Carregar lista de clientes"""
        try:
            # Limpar treeview
            for item in self.tree_clientes.get_children():
                self.tree_clientes.delete(item)
            
            # Buscar clientes no banco
            from database import DatabaseManager
            db = DatabaseManager()
            
            query = """
            SELECT id, nif, nome, telefone, tipo_cliente 
            FROM clientes 
            WHERE ativo = 1 
            ORDER BY nome
            LIMIT 50
            """
            
            clientes = db.connection_manager.execute_query(query, fetchall=True)
            
            for cliente in clientes:
                self.tree_clientes.insert('', 'end', 
                                         values=(cliente['nif'], cliente['nome'], cliente['telefone']),
                                         tags=(cliente['id'],))
            
            # Adicionar consumidor final
            self.tree_clientes.insert('', 0,
                                     values=('987654321', 'CONSUMIDOR FINAL', ''),
                                     tags=(1,))
            
        except Exception as e:
            self.logger.error(f"Erro ao carregar clientes: {e}")
    
    def buscar_cliente(self):
        """Buscar cliente por NIF"""
        nif = self.entry_nif_cliente.get().strip()
        
        if not nif:
            self.carregar_clientes()
            return
        
        try:
            # Limpar treeview
            for item in self.tree_clientes.get_children():
                self.tree_clientes.delete(item)
            
            # Buscar cliente específico
            from database import DatabaseManager
            db = DatabaseManager()
            
            query = """
            SELECT id, nif, nome, telefone, tipo_cliente 
            FROM clientes 
            WHERE (nif LIKE %s OR nome LIKE %s) 
              AND ativo = 1
            LIMIT 20
            """
            
            busca = f"%{nif}%"
            clientes = db.connection_manager.execute_query(query, (busca, busca), fetchall=True)
            
            for cliente in clientes:
                self.tree_clientes.insert('', 'end', 
                                         values=(cliente['nif'], cliente['nome'], cliente['telefone']),
                                         tags=(cliente['id'],))
            
            if not clientes:
                self.tree_clientes.insert('', 'end',
                                         values=('Não encontrado', '', ''))
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar cliente: {e}")
    
    def selecionar_cliente_da_lista(self, event):
        """Selecionar cliente da lista"""
        item = self.tree_clientes.selection()[0]
        valores = self.tree_clientes.item(item, 'values')
        tags = self.tree_clientes.item(item, 'tags')
        
        if valores[0] == 'Não encontrado':
            return
        
        cliente_id = int(tags[0])
        
        if cliente_id == 1:  # Consumidor Final
            self.selecionar_cliente_padrao()
        else:
            # Buscar dados completos do cliente
            try:
                from database import DatabaseManager
                db = DatabaseManager()
                
                cliente = db.get_client_by_id(cliente_id)
                
                if cliente:
                    self.cliente_atual = cliente
                    self.card_cliente.winfo_children()[1].config(
                        text=f"{cliente['nome'][:15]}"
                    )
                    
                    self.set_display_message(
                        "CLIENTE SELECIONADO",
                        cliente['nome'],
                        f"NIF: {cliente['nif']}"
                    )
            
            except Exception as e:
                self.logger.error(f"Erro ao selecionar cliente: {e}")
        
        # Fechar janela
        if hasattr(self, 'janela_cliente'):
            self.janela_cliente.destroy()
    
    def selecionar_cliente_padrao(self):
        """Selecionar consumidor final"""
        self.cliente_atual = {
            'id': 1,
            'nif': '654326789',
            'nome': 'CONSUMIDOR FINAL',
            'tipo': 'Consumidor Final'
        }
        self.card_cliente.winfo_children()[1].config(text="CONSUMIDOR FINAL")
        
        if hasattr(self, 'janela_cliente'):
            self.janela_cliente.destroy()
        
        self.set_display_message(
            "CLIENTE",
            "CONSUMIDOR FINAL",
            ""
        )
        
    def processar_opcao_cliente(self, opcao: str):
        """Processar opção de cliente"""
        if opcao == '1':
            # Consumidor Final
            self.cliente_atual = {
                'id': 1,
                'nif': '234567890',
                'nome': 'CONSUMIDOR FINAL',
                'tipo': 'Consumidor Final'
            }
            self.card_cliente.winfo_children()[1].config(text="CONSUMIDOR FINAL")
            
        elif opcao == '2':
            # Digitar NIF
            self.set_display_message(
                "DIGITAR NIF",
                "9 OU 14 DÍGITOS",
                "ENTER para consultar"
            )
            self.aguardando_nif_cliente = True
        
    def anular_item(self):
        """Anular item do carrinho"""
        if not self.carrinho:
            self.set_display_message(
                "ERRO",
                "CARRINHO VAZIO",
                ""
            )
            return
        
        self.set_display_message(
            "ANULAR ITEM",
            "DIGITE NÚMERO DO ITEM",
            "ENTER para confirmar"
        )
    
    def cancelar_venda(self):
        """Cancelar venda atual"""
        if not self.carrinho:
            return
        
        # Confirmar cancelamento
        resposta = messagebox.askyesno(
            "Cancelar Venda",
            "Tem certeza que deseja cancelar a venda atual?"
        )
        
        if resposta:
            self.carrinho.clear()
            self.atualizar_lista_produtos()
            self.atualizar_totais()
            self.set_display_message(
                "VENDA CANCELADA",
                "",
                ""
            )

    def aplicar_desconto(self):
        """Aplicar desconto na venda atual"""
        if not self.carrinho:
            self.set_display_message(
                "ERRO",
                "CARRINHO VAZIO",
                "ADICIONE PRODUTOS PRIMEIRO"
            )
            return
        
        self.set_display_message(
            "APLICAR DESCONTO",
            "DIGITE VALOR DO DESCONTO (Kz)",
            "ENTER para confirmar"
        )
        
        # Mudar para modo desconto
        self.modo_anterior = self.modo_atual
        self.modo_atual = 'desconto'  # MUDAR PARA 'desconto' em vez de 'aplicar_desconto'
        self.tipo_desconto = 'global'


    def processar_desconto(self, valor_str: str):
        """Processar valor de desconto digitado"""
        try:
            # Converter valor
            valor_str = valor_str.replace(',', '.')
            desconto_valor = float(valor_str)
            
            if desconto_valor <= 0:
                self.set_display_message(
                    "ERRO",
                    "DESCONTO INVÁLIDO",
                    "VALOR DEVE SER > 0"
                )
                return
            
            # Calcular total atual
            total_atual = sum(item['total'] for item in self.carrinho)
            
            # Verificar se desconto não excede total
            if desconto_valor > total_atual:
                self.set_display_message(
                    "ERRO",
                    "DESCONTO EXCEDE TOTAL",
                    f"TOTAL: {self.formatar_moeda(total_atual)}"
                )
                return
            
            # Armazenar desconto global
            self.desconto_global = desconto_valor
            self.total_com_desconto = total_atual - desconto_valor
            
            # Atualizar carrinho com desconto proporcional
            for item in self.carrinho:
                proporcao = item['total'] / total_atual
                desconto_item = desconto_valor * proporcao
                item['total'] = round(item['total'] - desconto_item, 2)
                item['desconto_valor'] = round(desconto_item, 2)
                item['desconto_percentual'] = round((desconto_item / item['total']) * 100, 2) if item['total'] > 0 else 0
            
            # Atualizar interface
            self.atualizar_lista_produtos()
            self.atualizar_totais()
            
            self.set_display_message(
                "DESCONTO APLICADO",
                f"VALOR: {self.formatar_moeda(desconto_valor)}",
                f"TOTAL FINAL: {self.formatar_moeda(self.total_com_desconto)}"
            )
            
            # Voltar para modo venda após 3 segundos
            self.root.after(3000, lambda: self.atualizar_modo('venda'))
            
        except ValueError:
            self.set_display_message(
                "ERRO",
                "VALOR INVÁLIDO",
                "DIGITE VALOR NUMÉRICO"
            )
        except Exception as e:
            self.logger.error(f"Erro ao aplicar desconto: {e}")
            self.set_display_message(
                "ERRO NO DESCONTO",
                str(e)[:30],
                ""
            )
    
    def corrigir_pagamento(self):
        """Corrigir pagamento"""
        self.set_display_message(
            "CORRIGIR PAGAMENTO",
            "SELECIONE PAGAMENTO PARA CORRIGIR",
            ""
        )
    
    def handle_scanned_code(self, code: str):
        """Processar código escaneado"""
        self.logger.info(f"Código escaneado recebido: {code}")
        
        if self.modo_atual == 'supervisor':
            # Modo supervisor - processar cartão
            self.handle_supervisor_barcode(code)
            return
        
        # Verificar se o scanner está disponível
        if not SCANNER_AVAILABLE:
            self.logger.warning("Scanner não disponível, ignorando código")
            return
        
        # Se estiver no modo venda ou consulta preço
        if self.modo_atual in ['venda', 'consultar_preco']:
            # Se tem quantidade pendente
            if self.quantidade_pendente:
                # Adicionar produto com quantidade específica
                self.input_buffer = code
                self.adicionar_produto()
            else:
                # Consultar preço ou adicionar com quantidade 1
                self.input_buffer = code
                
                if self.modo_atual == 'consultar_preco':
                    self.consultar_preco_buffer()
                else:
                    self.adicionar_produto()
        
        elif self.modo_atual == 'login':
            # Scanner pode ser usado para login rápido (cartão funcionário)
            self.input_buffer = code
            self.processar_enter()
        
        self.logger.info(f"Processado código: {code}")
    
    def modo_balanca(self):
        """Stub para modo balança"""
        self.set_display_message(
            "MODO BALANÇA",
            "FUNCIONALIDADE EM DESENVOLVIMENTO",
            ""
        )
    
    def pagamento_multiplas_formas(self):
        """Stub para pagamento múltiplas formas"""
        self.set_display_message(
            "PAGAMENTO MÚLTIPLO",
            "FUNCIONALIDADE EM DESENVOLVIMENTO",
            "USE UMA FORMA POR VEZ"
        )
    
    def aplicar_desconto_(self):
        """Stub para aplicar desconto"""
        self.set_display_message(
            "APLICAR DESCONTO",
            "DIGITE VALOR DO DESCONTO",
            "ENTER para confirmar"
        )

    def corrigir_pagamento(self):
        """Corrigir pagamento atual"""
        if hasattr(self, 'formas_pagamento') and self.formas_pagamento:
            # Remover última forma de pagamento
            ultima_forma = self.formas_pagamento.pop()
            self.valor_restante += ultima_forma['valor']
            
            self.set_display_message(
                "PAGAMENTO CORRIGIDO",
                f"REMOVIDO: {ultima_forma['forma']}",
                f"RESTANTE: {self.formatar_moeda(self.valor_restante)}"
            )
        else:
            self.set_display_message(
                "CORRIGIR PAGAMENTO",
                "NENHUM PAGAMENTO REGISTRADO",
                ""
            )

    def cancelar_pagamento(self):
        """Cancelar modo pagamento"""
        self.atualizar_modo('venda')
        
    def debug_login(self):
        """Método de debug para login"""
        print(f"Buffer: {self.input_buffer}")
        print(f"Tem login_worker_id: {hasattr(self, 'login_worker_id')}")
        if hasattr(self, 'login_worker_id'):
            print(f"login_worker_id: {self.login_worker_id}")
    
    
    
    def modo_sangria_p(self):
        """Entrar no modo sangria"""
        if not self.verificar_permissao('sangria'):
            self.set_display_message(
                "PERMISSÃO NEGADA",
                "ACESSO RESTRITO",
                "CONSULTE O SUPERVISOR"
            )
            return
        
        self.atualizar_modo('sangria')
        self.set_display_message(
            "MODO SANGRIA",
            "DIGITE VALOR DA SANGRIA",
            "SELECIONE FORMA DE PAGAMENTO"
        )
    
    def modo_devolucao(self):
        """Entrar no modo devolução"""
        self.atualizar_modo('devolucao')
        self.set_display_message(
            "MODO DEVOLUÇÃO",
            "DIGITE NÚMERO DO DOCUMENTO",
            "ENTER para consultar"
        )
    
    def fechar_caixa_p(self):
        """Fechar caixa atual"""
        if not self.verificar_permissao('fechar_caixa'):
            self.set_display_message(
                "PERMISSÃO NEGADA",
                "SOMENTE GERENTE/SUPERVISOR",
                ""
            )
            return
        
        resposta = messagebox.askyesno(
            "Fechar Caixa",
            "Tem certeza que deseja fechar o caixa?\nEsta operação não pode ser desfeita."
        )
        
        if resposta:
            self.set_display_message(
                "FECHAMENTO DE CAIXA",
                "PROCESSANDO...",
                ""
            )
            # Implementar fechamento de caixa
    
    def abrir_gaveta(self):
        """Abrir gaveta de dinheiro"""
        try:
            from printer_manager import printer_manager
            # Simular comando de abrir gaveta
            printer_manager._open_cash_drawer()
            self.set_display_message(
                "GAVETA ABERTA",
                "",
                ""
            )
        except Exception as e:
            self.logger.error(f"Erro ao abrir gaveta: {e}")
    
    def teste_impressora(self):
        """Testar impressora"""
        try:
            from printer_manager import printer_manager
            printer_manager.print_test_page()
            self.set_display_message(
                "TESTE IMPRESSORA",
                "IMPRIMINDO...",
                "VERIFIQUE A IMPRESSORA"
            )
        except Exception as e:
            self.logger.error(f"Erro no teste impressora: {e}")
    
    def relatorio_diario(self):
        """Gerar relatório diário"""
        self.set_display_message(
            "RELATÓRIO DIÁRIO",
            "GERANDO...",
            ""
        )
        # Implementar geração de relatório
    
    def abrir_configuracoes(self):
        """Abrir configurações do sistema"""
        if not self.verificar_permissao('configuracoes'):
            self.set_display_message(
                "PERMISSÃO NEGADA",
                "SOMENTE ADMINISTRADOR",
                ""
            )
            return
        
        self.set_display_message(
            "CONFIGURAÇÕES",
            "EM DESENVOLVIMENTO",
            ""
        )
        # Implementar janela de configurações
    
    def voltar_modo_venda(self):
        """Voltar para modo venda"""
        self.atualizar_modo('venda')
    
    def voltar_modo_funcoes(self):
        """Voltar para modo funções"""
        self.atualizar_modo('funcoes')
    
    def voltar_modo_anterior(self):
        """Voltar para modo anterior"""
        if hasattr(self, 'modo_anterior'):
            self.atualizar_modo(self.modo_anterior)
        else:
            self.atualizar_modo('venda')
    
    def processar_sangria(self, forma: str):
        """Processar sangria"""
        self.set_display_message(
            "SANGRIA",
            f"FORMA: {forma}",
            "DIGITE VALOR"
        )
        self.aguardando_valor_sangria = True
        self.forma_sangria = forma
    
    def terminar_sangria(self):
        """Terminar operação de sangria"""
        if hasattr(self, 'valor_sangria') and self.valor_sangria > 0:
            self.set_display_message(
                "SANGRIA REGISTRADA",
                f"VALOR: {self.formatar_moeda(self.valor_sangria)}",
                f"FORMA: {self.forma_sangria}"
            )
            # Registrar sangria no banco
            delattr(self, 'valor_sangria')
            delattr(self, 'forma_sangria')
            delattr(self, 'aguardando_valor_sangria')
        else:
            self.set_display_message(
                "ERRO",
                "NENHUM VALOR DIGITADO",
                ""
            )
    
    def cancelar_sangria(self):
        """Cancelar sangria"""
        for attr in ['valor_sangria', 'forma_sangria', 'aguardando_valor_sangria']:
            if hasattr(self, attr):
                delattr(self, attr)
        self.atualizar_modo('funcoes')
    
    def devolucao_parcial(self):
        """Iniciar devolução parcial"""
        self.set_display_message(
            "DEVOLUÇÃO PARCIAL",
            "DIGITE Nº DOCUMENTO",
            "ENTER para consultar"
        )
        self.tipo_devolucao = 'parcial'
    
    def devolucao_total(self):
        """Iniciar devolução total"""
        self.set_display_message(
            "DEVOLUÇÃO TOTAL",
            "DIGITE Nº DOCUMENTO",
            "ENTER para consultar"
        )
        self.tipo_devolucao = 'total'
    
    def consultar_documento(self):
        """Consultar documento para devolução"""
        if hasattr(self, 'input_buffer') and self.input_buffer:
            self.set_display_message(
                "CONSULTANDO DOCUMENTO",
                f"Nº: {self.input_buffer}",
                "AGUARDE..."
            )
            # Implementar consulta ao banco
    
    def terminar_devolucao(self):
        """Terminar devolução"""
        self.set_display_message(
            "DEVOLUÇÃO CONCLUÍDA",
            "",
            ""
        )
        self.atualizar_modo('funcoes')
    
    def cancelar_devolucao(self):
        """Cancelar devolução"""
        for attr in ['tipo_devolucao', 'documento_devolucao']:
            if hasattr(self, attr):
                delattr(self, attr)
        self.atualizar_modo('funcoes')

    def verificar_permissao(self, operacao: str) -> bool:
        """Verificar permissão do usuário para operação"""
        if not hasattr(self, 'usuario_atual'):
            return False
        
        perfil = self.usuario_atual.get('perfil', 'operador')
        
        permissoes = {
            'admin': ['sangria', 'fechar_caixa', 'configuracoes', 'relatorios'],
            'gerente': ['sangria', 'fechar_caixa', 'relatorios'],
            'supervisor': ['sangria', 'relatorios'],
            'operador': []
        }
        
        return operacao in permissoes.get(perfil, [])
    
    def _criar_botao_funcao(self, texto: str, cor: str, icone: str, comando):
        """Criar botão de função no container"""
        btn_frame = tk.Frame(self.funcoes_container, bg=self.cores['fundo_medio'])
        btn_frame.pack(fill='x', padx=5, pady=3)
        
        # Verificar se o botão está disponível
        disponivel = True
        
        # Verificar permissões para certos botões
        if texto in ['SANGRIA', 'FECHAR CAIXA', 'CONFIGURAÇÕES']:
            if hasattr(self, 'usuario_atual'):
                perfil = self.usuario_atual.get('perfil', 'operador')
                if perfil not in ['admin', 'gerente', 'supervisor']:
                    disponivel = False
                    cor = self.cores['texto_secundario']
        
        btn = tk.Button(btn_frame, text=f"{icone}\n{texto}",
                      bg=cor, fg='white',
                      font=('Arial', 10, 'bold'),
                      width=25, height=2,
                      command=comando if disponivel else lambda: None,
                      justify='center',
                      state='normal' if disponivel else 'disabled',
                      cursor='hand2' if disponivel else 'arrow')
        
        # Tooltip para botões desabilitados
        if not disponivel:
            self._criar_tooltip(btn, "Acesso restrito - Permissão necessária")
        
        btn.pack(fill='x', padx=5, pady=2)
    
    def _criar_tooltip(self, widget, text):
        """Criar tooltip para widget"""
        def on_enter(event):
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25
            
            # Criar tooltip
            self.tooltip = tk.Toplevel(widget)
            self.tooltip.wm_overrideredirect(True)
            self.tooltip.wm_geometry(f"+{x}+{y}")
            
            label = tk.Label(self.tooltip, text=text, 
                            bg='yellow', fg='black',
                            font=('Arial', 8))
            label.pack()
        
        def on_leave(event):
            if hasattr(self, 'tooltip'):
                self.tooltip.destroy()
        
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
    
    def _atualizar_scroll_funcoes(self):
        """Atualizar scroll do container de funções"""
        if hasattr(self, 'canvas_funcoes'):
            self.canvas_funcoes.configure(scrollregion=self.canvas_funcoes.bbox("all"))
            
############  novo ini

    def abrir_caixa(self):
        """Abrir caixa (nova funcionalidade)"""
        if not hasattr(self, 'usuario_atual'):
            self.set_display_message(
                "ERRO",
                "USUÁRIO NÃO LOGADO",
                "FAÇA LOGIN PRIMEIRO"
            )
            return
        
        # CORREÇÃO: Importar datetime corretamente
        from datetime import datetime
        
        # Criar janela de abertura de caixa
        self.janela_abertura = tk.Toplevel(self.root)
        self.janela_abertura.title("Abertura de Caixa")
        self.janela_abertura.geometry("400x300")
        self.janela_abertura.configure(bg=self.cores['fundo_medio'])
        self.janela_abertura.transient(self.root)
        self.janela_abertura.grab_set()
        
        # Centralizar
        self.janela_abertura.update_idletasks()
        width = self.janela_abertura.winfo_width()
        height = self.janela_abertura.winfo_height()
        x = (self.janela_abertura.winfo_screenwidth() // 2) - (width // 2)
        y = (self.janela_abertura.winfo_screenheight() // 2) - (height // 2)
        self.janela_abertura.geometry(f'{width}x{height}+{x}+{y}')
        
        # Conteúdo
        tk.Label(self.janela_abertura, text="ABERTURA DE CAIXA", 
                bg=self.cores['fundo_medio'], fg=self.cores['texto_primario'],
                font=('Arial', 16, 'bold')).pack(pady=20)
        
        info_frame = tk.Frame(self.janela_abertura, bg=self.cores['fundo_card'], padx=20, pady=20)
        info_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Operador
        tk.Label(info_frame, text=f"Operador: {self.usuario_atual['nome']}", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 11)).pack(anchor='w', pady=5)
        
        # PDV
        tk.Label(info_frame, text=f"PDV: {self.pdv_config['pdv_id']}", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 11)).pack(anchor='w', pady=5)
        
        # Data/Hora - CORRIGIDO
        data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
        tk.Label(info_frame, text=f"Data: {data_hora}", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 11)).pack(anchor='w', pady=5)
        
        # Valor de abertura
        tk.Label(info_frame, text="Valor de Abertura (Kz):", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 11, 'bold')).pack(anchor='w', pady=(15, 5))
        
        self.entry_valor_abertura = tk.Entry(info_frame, width=20, 
                                            font=('Arial', 14), justify='right')
        self.entry_valor_abertura.insert(0, "0,00")
        self.entry_valor_abertura.pack(pady=5)
        self.entry_valor_abertura.focus_set()
        self.entry_valor_abertura.select_range(0, tk.END)
        
        # Botões
        botoes_frame = tk.Frame(self.janela_abertura, bg=self.cores['fundo_medio'])
        botoes_frame.pack(pady=20)
        
        btn_confirmar = tk.Button(botoes_frame, text="✓ CONFIRMAR",
                                bg=self.cores['sucesso'], fg='white',
                                font=('Arial', 12, 'bold'),
                                width=15, height=2,
                                command=self.confirmar_abertura_caixa)
        btn_confirmar.pack(side='left', padx=10)
        
        btn_cancelar = tk.Button(botoes_frame, text="✗ CANCELAR",
                               bg=self.cores['erro'], fg='white',
                               font=('Arial', 12, 'bold'),
                               width=15, height=2,
                               command=self.janela_abertura.destroy)
        btn_cancelar.pack(side='left', padx=10)
    
    def confirmar_abertura_caixa(self):
        """Confirmar abertura de caixa"""
        try:
            valor_str = self.entry_valor_abertura.get().replace(',', '.')
            valor_abertura = float(valor_str)
            
            if valor_abertura < 0:
                messagebox.showerror("Erro", "Valor de abertura não pode ser negativo")
                return
            
            # Criar sessão usando SessionManager
            from session_manager import session_manager
            
            session_id = session_manager.create_caixa_session(
                pdv_id=int(self.pdv_config['pdv_id']),
                usuario_id=self.usuario_atual['id'],
                loja_id=int(self.pdv_config['loja_id']),
                valor_abertura=valor_abertura
            )
            
            if session_id:
                # Atualizar interface
                if hasattr(self, 'info_widgets') and len(self.info_widgets) > 4:
                    self.info_widgets[4].config(
                        text="● ABERTO",
                        fg=self.cores['sucesso']
                    )
                
                self.set_display_message(
                    "CAIXA ABERTO",
                    f"VALOR: {self.formatar_moeda(valor_abertura)}",
                    "PRONTO PARA VENDAS"
                )
                
                # Fechar janela
                self.janela_abertura.destroy()
                
                # Mostrar mensagem de sucesso
                messagebox.showinfo("Sucesso", 
                                  f"Caixa aberto com sucesso!\nValor inicial: {self.formatar_moeda(valor_abertura)}")
            else:
                messagebox.showerror("Erro", "Não foi possível abrir o caixa. Verifique se já existe uma sessão aberta.")
                
        except ValueError:
            messagebox.showerror("Erro", "Valor inválido. Digite um valor numérico.")
 
    #############superv ini 

    def modo_supervisor(self):
        """Entrar em modo supervisor"""
        self.set_display_message(
            "MODO SUPERVISOR",
            "PASSE CARTÃO SUPERVISOR",
            "OU DIGITE CÓDIGO"
        )
        
        # Configurar timeout
        self.supervisor_timeout = 30  # segundos
        self.supervisor_start_time = time.time()
        
        # Verificar se está no modo funções
        self.modo_anterior = self.modo_atual
        self.modo_atual = 'supervisor'
        
        # Iniciar contador de timeout
        self._check_supervisor_timeout()
    
    def _check_supervisor_timeout(self):
        """Verificar timeout do modo supervisor"""
        if self.modo_atual == 'supervisor':
            elapsed = time.time() - self.supervisor_start_time
            remaining = self.supervisor_timeout - elapsed
            
            if remaining <= 0:
                # Timeout atingido
                self.set_display_message(
                    "TEMPO ESGOTADO",
                    "MODO SUPERVISOR CANCELADO",
                    ""
                )
                self.atualizar_modo(self.modo_anterior)
                return
            
            # Atualizar display
            if remaining <= 10:
                self.set_display_message(
                    "MODO SUPERVISOR",
                    f"TEMPO: {int(remaining)} segundos",
                    "PASSE CARTÃO SUPERVISOR"
                )
            
            # Verificar novamente em 1 segundo
            self.root.after(1000, self._check_supervisor_timeout)
    
    def handle_supervisor_barcode(self, barcode: str):
        """Processar código de barras do supervisor"""
        try:
            # Obter códigos válidos do config
            valid_codes_str = config.get('SUPERVISOR', 'barcode_codes', '')
            valid_codes = [code.strip() for code in valid_codes_str.split(',') if code.strip()]
            
            if barcode in valid_codes:
                self.set_display_message(
                    "CARTÃO SUPERVISOR ACEITE",
                    "DIGITE Nº TRABALHADOR",
                    "ENTER para confirmar"
                )
                self.supervisor_authenticated = True
                self.modo_atual = 'supervisor_login'
            else:
                self.set_display_message(
                    "CARTÃO INVÁLIDO",
                    "CARTÃO SUPERVISOR NÃO RECONHECIDO",
                    "TENTE NOVAMENTE"
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao processar cartão supervisor: {e}")
    
    def processar_supervisor_login(self):
        """Processar login de supervisor"""
        if not hasattr(self, 'supervisor_worker_id'):
            # Primeira etapa: worker ID
            worker_id = self.input_buffer
            
            if len(worker_id) != 4 or not worker_id.isdigit():
                self.set_display_message(
                    "ERRO",
                    "NÚMERO TRABALHADOR INVÁLIDO",
                    "DEVE TER 4 DÍGITOS"
                )
                self.input_buffer = ""
                return
            
            self.supervisor_worker_id = worker_id
            self.set_display_message(
                "SUPERVISOR LOGIN",
                f"TRABALHADOR: {worker_id}",
                "DIGITE SENHA (5 dígitos)"
            )
            self.input_buffer = ""
        
        else:
            # Segunda etapa: senha
            senha = self.input_buffer
            
            # Validar credenciais
            sucesso, usuario = auth_manager.validate_credentials(
                self.supervisor_worker_id, senha
            )
            
            if sucesso and usuario:
                # Verificar se é supervisor ou admin
                perfil = usuario['perfil']
                if perfil in ['supervisor', 'admin', 'gerente']:
                    self.supervisor_usuario = usuario
                    self.set_display_message(
                        "SUPERVISOR AUTORIZADO",
                        f"BEM-VINDO, {usuario['nome']}",
                        f"PERFIL: {perfil.upper()}"
                    )
                    
                    # Limpar estado
                    delattr(self, 'supervisor_worker_id')
                    self.input_buffer = ""
                    
                    # Mudar para modo supervisor ativo
                    self.modo_atual = 'supervisor_ativo'
                    self.atualizar_botoes_modo()
                    
                else:
                    self.set_display_message(
                        "PERMISSÃO NEGADA",
                        "APENAS SUPERVISORES",
                        "OU ADMINISTRADORES"
                    )
                    # Limpar
                    delattr(self, 'supervisor_worker_id')
                    self.input_buffer = ""
            else:
                self.set_display_message(
                    "ERRO DE LOGIN",
                    "CREDENCIAIS INVÁLIDAS",
                    "TENTE NOVAMENTE"
                )
                # Limpar
                delattr(self, 'supervisor_worker_id')
                self.input_buffer = ""

    def _aplicar_promocao_selecionada(self, tree, janela):
        """Aplicar promoção selecionada"""
        try:
            selecionado = tree.selection()
            if not selecionado:
                return
            
            item = selecionado[0]
            tags = tree.item(item, 'tags')
            
            if not tags or tags[0] == '':
                return
            
            promocao_id = int(tags[0])
            
            # Buscar detalhes da promoção
            from database import DatabaseManager
            from promotion_manager import promotion_manager
            db = DatabaseManager()
            
            query = """
            SELECT p.*, tp.nome as tipo_nome
            FROM promocoes p
            JOIN tipos_promocao tp ON p.tipo_promocao_id = tp.id
            WHERE p.id = %s
            """
            
            promocao = db.connection_manager.execute_query(query, (promocao_id,), fetchone=True)
            
            if not promocao:
                messagebox.showerror("Erro", "Promoção não encontrada")
                return
            
            # Aplicar promoção ao carrinho
            promocoes_aplicadas = []
            
            for item_carrinho in self.carrinho:
                produto_id = item_carrinho['produto_id']
                
                # Verificar se promoção se aplica a este produto
                aplicaveis = promotion_manager.check_promotions_for_product(
                    produto_id, 
                    item_carrinho['quantidade'],
                    cliente_id=self.cliente_atual.get('id') if hasattr(self, 'cliente_atual') else None,
                    total_venda=sum(i['total'] for i in self.carrinho)
                )
                
                for promo_aplicavel in aplicaveis:
                    if promo_aplicavel['promocao_id'] == promocao_id:
                        # Calcular desconto
                        desconto_info = promo_aplicavel['desconto']
                        valor_original = item_carrinho['total']
                        
                        if desconto_info['tipo'] == 'percentual':
                            desconto_valor = valor_original * (desconto_info['valor'] / 100)
                        elif desconto_info['tipo'] == 'fixo':
                            desconto_valor = desconto_info['valor']
                        else:
                            continue  # Outros tipos precisam de lógica adicional
                        
                        # Aplicar desconto
                        item_carrinho['total'] = round(item_carrinho['total'] - desconto_valor, 2)
                        item_carrinho['desconto_valor'] = round(desconto_valor, 2)
                        item_carrinho['desconto_promocao'] = promocao_id
                        
                        promocoes_aplicadas.append({
                            'nome': promocao['nome'],
                            'valor_desconto': desconto_valor,
                            'produto': item_carrinho['descricao']
                        })
            
            if promocoes_aplicadas:
                # Atualizar interface
                self.atualizar_lista_produtos()
                self.atualizar_totais()
                
                # Mostrar resumo
                resumo = "\n".join([f"• {p['produto']}: -{self.formatar_moeda(p['valor_desconto'])}" 
                                  for p in promocoes_aplicadas])
                
                messagebox.showinfo("Promoção Aplicada", 
                                  f"Promoção '{promocao['nome']}' aplicada com sucesso!\n\nDescontos aplicados:\n{resumo}")
                
                # Armazenar promoções aplicadas
                if not hasattr(self, 'promocoes_aplicadas'):
                    self.promocoes_aplicadas = []
                self.promocoes_aplicadas.extend(promocoes_aplicadas)
                
                # Fechar janela
                janela.destroy()
                
                # Voltar para modo venda
                self.atualizar_modo('venda')
            else:
                messagebox.showwarning("Sem aplicação", 
                                     f"A promoção '{promocao['nome']}' não se aplica aos produtos no carrinho.")
                
        except Exception as e:
            self.logger.error(f"Erro ao aplicar promoção: {e}")
            messagebox.showerror("Erro", f"Erro ao aplicar promoção: {str(e)}")
    

    def aplicar_promocao_manual(self):
        """Aplicar promoção manualmente (modo supervisor)"""
        if not self.carrinho:
            self.set_display_message(
                "ERRO",
                "CARRINHO VAZIO",
                "ADICIONE PRODUTOS PRIMEIRO"
            )
            return
        
        # Criar janela de seleção de promoção
        self._criar_janela_promocoes()
    
    def _criar_janela_promocoes(self):
        """Criar janela de seleção de promoções"""
        janela = tk.Toplevel(self.root)
        janela.title("Aplicar Promoção")
        janela.geometry("600x500")
        janela.configure(bg=self.cores['fundo_medio'])
        janela.transient(self.root)
        janela.grab_set()
        
        # Título
        tk.Label(janela, text="SELECIONAR PROMOÇÃO", 
                bg=self.cores['fundo_medio'], fg=self.cores['texto_primario'],
                font=('Arial', 16, 'bold')).pack(pady=20)
        
        # Frame de lista
        frame_lista = tk.Frame(janela, bg=self.cores['fundo_card'])
        frame_lista.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Treeview de promoções
        columns = ('codigo', 'nome', 'tipo', 'validade')
        tree = ttk.Treeview(frame_lista, columns=columns, show='headings', height=15)
        
        tree.heading('codigo', text='Código')
        tree.heading('nome', text='Nome')
        tree.heading('tipo', text='Tipo')
        tree.heading('validade', text='Validade')
        
        tree.column('codigo', width=100)
        tree.column('nome', width=250)
        tree.column('tipo', width=100)
        tree.column('validade', width=120)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_lista, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Carregar promoções
        self._carregar_promocoes_tree(tree)
        
        # Botão aplicar
        btn_frame = tk.Frame(janela, bg=self.cores['fundo_medio'])
        btn_frame.pack(pady=20)
        
        btn_aplicar = tk.Button(btn_frame, text="APLICAR PROMOÇÃO",
                              bg=self.cores['sucesso'], fg='white',
                              font=('Arial', 12, 'bold'),
                              width=20, height=2,
                              command=lambda: self._aplicar_promocao_selecionada(tree, janela))
        btn_aplicar.pack()
        
        # Bind duplo clique
        tree.bind('<Double-1>', lambda e: self._aplicar_promocao_selecionada(tree, janela))

    def _carregar_promocoes_tree(self, tree):
        """Carregar promoções ativas na treeview - MÉTODO COMPLETO"""
        try:
            # Limpar treeview
            for item in tree.get_children():
                tree.delete(item)
            
            self.logger.info("Carregando promoções ativas...")
            
            # Buscar promoções ativas
            query = """
            SELECT p.id, p.codigo, p.nome, tp.nome as tipo, 
                   CONCAT(DATE_FORMAT(p.data_inicio, '%d/%m'), ' a ', 
                          DATE_FORMAT(p.data_fim, '%d/%m/%Y')) as validade
            FROM promocoes p
            JOIN tipos_promocao tp ON p.tipo_promocao_id = tp.id
            WHERE p.ativo = 1 
              AND CURDATE() BETWEEN p.data_inicio AND p.data_fim
            ORDER BY p.nome
            """
            
            promocoes = connection_pool.execute_query(query, fetchall=True)
            
            self.logger.info(f"Encontradas {len(promocoes) if promocoes else 0} promoções")
            
            if promocoes:
                for promocao in promocoes:
                    tree.insert('', 'end', 
                               values=(promocao['codigo'], promocao['nome'], 
                                       promocao['tipo'], promocao['validade']),
                               tags=(promocao['id'],))
            else:
                tree.insert('', 'end', 
                           values=('NENHUMA', 'Sem promoções ativas', '', ''))
                
        except Exception as e:
            self.logger.error(f"Erro ao carregar promoções: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            tree.insert('', 'end', 
                       values=('ERRO', str(e)[:30], '', ''))

########### nono fim            
###########sangria ini 

    def modo_sangria(self):
        """Entrar no modo sangria avançado - COM DEBUG DETALHADO"""
        if not hasattr(self, 'usuario_atual'):
            self.set_display_message("ERRO", "FAÇA LOGIN", "")
            return
        
        self.logger.info("=== DEBUG MODO SANGRIA ===")
        
        # Verificar se há sessão aberta
        from session_manager import session_manager
        pdv_id = int(self.pdv_config['pdv_id'])
        sessao = session_manager.get_active_session(pdv_id)
        
        if not sessao:
            self.set_display_message("ERRO", "CAIXA FECHADO", "ABRA O CAIXA PRIMEIRO")
            return
        
        self.sessao_sangria = sessao['session_id']
        self.logger.info(f"Sessão encontrada: ID={self.sessao_sangria}")
        
        # Carregar formas de pagamento com valores
        from caixa_manager import caixa_manager
        formas = caixa_manager.get_formas_pagamento_com_valor(
            self.sessao_sangria, 
            pdv_id
        )
        
        self.logger.info(f"=== RESULTADOS DA CONSULTA ===")
        self.logger.info(f"Total formas retornadas: {len(formas)}")
        
        if formas:
            for i, forma in enumerate(formas):
                self.logger.info(f"[{i+1}] {forma['nome']} ({forma['codigo']})")
                self.logger.info(f"     Sistema: {forma.get('valor_sistema', 0)}")
                self.logger.info(f"     Sangrias: {forma.get('valor_sangrias', 0)}")
                self.logger.info(f"     Disponível: {forma.get('valor_disponivel', 0)}")
                self.logger.info(f"     ID: {forma.get('id')}")
        else:
            self.logger.warning("NENHUMA FORMA RETORNADA!")
            # Testar consulta direta
            self._testar_consulta_formas(pdv_id)
        
        if not formas or len(formas) == 0:
            self.set_display_message(
                "SEM MOVIMENTOS",
                "FAÇA VENDAS PRIMEIRO",
                "OU CAIXA SEM VALORES"
            )
            # Mostrar botões básicos apenas
            self.sangria_ativa = True
            self.sangria_formas = []
            self.modo_atual = 'sangria_avancada'
            self.atualizar_botoes_modo()
            return
        
        # Inicializar estado da sangria
        self.sangria_ativa = True
        self.sangria_formas = formas
        self.sangria_detalhes = []
        self.sangria_forma_atual = None
        
        self.set_display_message(
            "MODO SANGRIA",
            f"FORMAS: {len(formas)} ENCONTRADAS",
            "SELECIONE FORMA DE PAGAMENTO"
        )
        
        # Mudar modo
        self.modo_atual = 'sangria_avancada'
        self.atualizar_botoes_modo()
        
        self.logger.info("=== MODO SANGRIA CONFIGURADO ===")
    
    def _testar_consulta_formas(self, pdv_id: int):
        """Testar consulta direta ao banco"""
        try:
            from connection_manager import connection_pool
            
            # Teste 1: Formas de pagamento ativas
            query1 = "SELECT COUNT(*) as total FROM forma_pagamento WHERE ativo = 1"
            result1 = connection_pool.execute_query(query1, fetchone=True)
            self.logger.info(f"Formas ativas no banco: {result1['total'] if result1 else 0}")
            
            # Teste 2: Vendas hoje
            query2 = """
            SELECT COUNT(*) as total_vendas, COALESCE(SUM(total_pago), 0) as total_pago
            FROM vendas 
            WHERE pdv_id = %s 
                AND DATE(data_emissao) = CURDATE()
                AND estado = 'EMITIDO'
            """
            result2 = connection_pool.execute_query(query2, (pdv_id,), fetchone=True)
            self.logger.info(f"Vendas hoje: {result2['total_vendas']}, Total: {result2['total_pago']}")
            
            # Teste 3: Formas com vendas
            query3 = """
            SELECT fp.nome, fp.codigo, COUNT(v.id) as qtd_vendas, 
                   COALESCE(SUM(v.total_pago), 0) as total
            FROM forma_pagamento fp
            LEFT JOIN vendas v ON fp.id = v.forma_pagamento_id 
                AND v.pdv_id = %s 
                AND DATE(v.data_emissao) = CURDATE()
                AND v.estado = 'EMITIDO'
            WHERE fp.ativo = 1
            GROUP BY fp.id, fp.nome, fp.codigo
            ORDER BY fp.nome
            """
            result3 = connection_pool.execute_query(query3, (pdv_id,), fetchall=True)
            
            self.logger.info("=== DETALHE POR FORMA ===")
            for item in result3:
                self.logger.info(f"{item['nome']} ({item['codigo']}): "
                               f"{item['qtd_vendas']} vendas, {item['total']} Kz")
        
        except Exception as e:
            self.logger.error(f"Erro no teste: {e}")
        
    def processar_sangria_forma(self, forma_codigo: str):
        """Selecionar forma de pagamento para sangria"""
        try:
            # Encontrar forma
            forma = next((f for f in self.sangria_formas if f['codigo'] == forma_codigo), None)
            
            if not forma:
                self.set_display_message("ERRO", "FORMA NÃO ENCONTRADA", "")
                return
            
            self.sangria_forma_atual = forma
            
            # Mostrar informações
            disponivel = forma.get('valor_disponivel', 0)
            sistema = forma.get('valor_sistema', 0)
            sangrias = forma.get('valor_sangrias', 0)
            
            self.set_display_message(
                f"SANGRIA - {forma['nome']}",
                f"DISPONÍVEL: {self.formatar_moeda(disponivel)}",
                f"DIGITE VALOR DA SANGRIA"
            )
            
            # Mudar para modo digitar valor
            self.modo_sangria_digitar = True
            
        except Exception as e:
            self.logger.error(f"Erro ao selecionar forma: {e}")
            self.set_display_message("ERRO", "ERRO NA SELEÇÃO", "")
    
    def processar_valor_sangria(self):
        """Processar valor digitado para sangria"""
        try:
            if not self.sangria_forma_atual or not self.input_buffer:
                self.set_display_message("ERRO", "DIGITE VALOR", "")
                return
            
            # Converter valor
            valor_str = self.input_buffer.replace(',', '.')
            valor_sangria = float(valor_str)
            
            if valor_sangria <= 0:
                self.set_display_message("ERRO", "VALOR INVÁLIDO", "")
                return
            
            forma = self.sangria_forma_atual
            disponivel = forma.get('valor_disponivel', 0)
            
            # Verificar se valor não excede disponível
            if valor_sangria > disponivel:
                self.set_display_message(
                    "ERRO", 
                    f"VALOR EXCEDE DISPONÍVEL",
                    f"DISPONÍVEL: {self.formatar_moeda(disponivel)}"
                )
                return
            
            # Calcular diferença
            valor_sistema = forma.get('valor_sistema', 0)
            diferenca = valor_sistema - valor_sangria
            
            # Armazenar sangria
            sangria_detalhe = {
                'forma_pagamento_id': forma['id'],
                'forma_nome': forma['nome'],
                'forma_codigo': forma['codigo'],
                'valor_sistema': valor_sistema,
                'valor_sangria': valor_sangria,
                'diferenca': diferenca,
                'timestamp': time.time()
            }
            
            self.sangria_detalhes.append(sangria_detalhe)
            
            # Atualizar forma disponível
            forma['valor_sangrias'] = forma.get('valor_sangrias', 0) + valor_sangria
            forma['valor_disponivel'] = forma.get('valor_sistema', 0) - forma['valor_sangrias']
            
            # Mostrar confirmação
            self.set_display_message(
                "SANGRIA REGISTRADA",
                f"{forma['nome']}: {self.formatar_moeda(valor_sangria)}",
                f"DIFERENÇA: {self.formatar_moeda(diferenca)}"
            )
            
            # Resetar estado
            self.sangria_forma_atual = None
            self.modo_sangria_digitar = False
            self.input_buffer = ""
            
            # Voltar para seleção de formas após 2 segundos
            self.root.after(2000, lambda: self.set_display_message(
                "MODO SANGRIA",
                "SELECIONE FORMA DE PAGAMENTO",
                f"RESTANTES: {len([f for f in self.sangria_formas if f['valor_disponivel'] > 0])}"
            ))
            
        except ValueError:
            self.set_display_message("ERRO", "VALOR INVÁLIDO", "USE NÚMEROS")
        except Exception as e:
            self.logger.error(f"Erro ao processar sangria: {e}")
            self.set_display_message("ERRO", "ERRO NA SANGRIA", "")
    
    def terminar_sangria(self):
        """Finalizar processo de sangria e salvar no banco"""
        try:
            if not self.sangria_detalhes:
                self.set_display_message("ERRO", "NENHUMA SANGRIA", "")
                return
            
            # Registrar cada sangria no banco
            from caixa_manager import caixa_manager
            
            for detalhe in self.sangria_detalhes:
                sucesso, movimento_id = caixa_manager.registrar_sangria(
                    sessao_id=self.sessao_sangria,
                    pdv_id=int(self.pdv_config['pdv_id']),
                    usuario_id=self.usuario_atual['id'],
                    forma_pagamento_id=detalhe['forma_pagamento_id'],
                    valor=detalhe['valor_sangria'],
                    valor_sistema=detalhe['valor_sistema'],
                    motivo=f"Sangria operador {self.usuario_atual['nome']}"
                )
                
                if sucesso:
                    detalhe['movimento_id'] = movimento_id
            
            # Imprimir comprovativo
            self._imprimir_comprovativo_sangria()
            
            # Mostrar resumo
            total_sangria = sum(d['valor_sangria'] for d in self.sangria_detalhes)
            total_diferenca = sum(d['diferenca'] for d in self.sangria_detalhes)
            
            self.set_display_message(
                "SANGRIA CONCLUÍDA",
                f"TOTAL: {self.formatar_moeda(total_sangria)}",
                f"DIFERENÇA: {self.formatar_moeda(total_diferenca)}"
            )
            
            # Limpar estado
            self._limpar_estado_sangria()
            
            # Voltar para modo funções após 3 segundos
            self.root.after(3000, lambda: self.atualizar_modo('funcoes'))
            
        except Exception as e:
            self.logger.error(f"Erro ao terminar sangria: {e}")
            self.set_display_message("ERRO", "ERRO AO SALVAR", "")
    
    def _imprimir_comprovativo_sangria(self):
        """Imprimir comprovativo de sangria"""
        try:
            from receipt_generator import receipt_generator
            
            comprovativo_data = {
                'tipo': 'COMPROVATIVO SANGRIA',
                'data_emissao': datetime.now().strftime("%d/%m/%Y %H:%M"),
                'operador_nome': self.usuario_atual['nome'],
                'pdv_id': self.pdv_config['pdv_id'],
                'loja_id': self.pdv_config['loja_id'],
                'sangrias': self.sangria_detalhes,
                'total_sangria': sum(d['valor_sangria'] for d in self.sangria_detalhes),
                'total_diferenca': sum(d['diferenca'] for d in self.sangria_detalhes),
                'quantidade_formas': len(self.sangria_detalhes)
            }
            
            # Gerar texto do comprovativo
            texto = self._gerar_texto_comprovativo(comprovativo_data)
            
            # Salvar em arquivo (para testes)
            filename = f"comprovativos/sangria_{int(time.time())}.txt"
            import os
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(texto)
            
            # Imprimir se configurado
            if config.getboolean('PRINTER', 'auto_print', True):
                from printer_manager import printer_manager
                
                print_job = {
                    'type': 'sangria',
                    'text': texto,
                    'timestamp': time.time()
                }
                
                printer_manager.print_queue.put(print_job)
            
            self.logger.info(f"Comprovativo de sangria gerado: {filename}")
            
        except Exception as e:
            self.logger.error(f"Erro ao imprimir comprovativo: {e}")
    
    def _gerar_texto_comprovativo(self, data: Dict) -> str:
        """Gerar texto do comprovativo de sangria"""
        lines = []
        line_width = 48
        
        lines.append("=" * line_width)
        lines.append("COMPROVANTE DE SANGRIA".center(line_width))
        lines.append("=" * line_width)
        
        lines.append(f"Data: {data['data_emissao']}")
        lines.append(f"Operador: {data['operador_nome']}")
        lines.append(f"PDV: {data['pdv_id']} - Loja: {data['loja_id']}")
        
        lines.append("-" * line_width)
        lines.append("DETALHES DA SANGRIA".center(line_width))
        lines.append("-" * line_width)
        
        lines.append(f"{'Forma':<15} {'Sistema':>10} {'Sangria':>10} {'Dif.':>10}")
        lines.append("-" * line_width)
        
        for sangria in data['sangrias']:
            linha = (f"{sangria['forma_nome'][:14]:<15} "
                    f"{self.formatar_moeda(sangria['valor_sistema'], False):>10} "
                    f"{self.formatar_moeda(sangria['valor_sangria'], False):>10} "
                    f"{self.formatar_moeda(sangria['diferenca'], False):>10}")
            lines.append(linha)
        
        lines.append("=" * line_width)
        lines.append(f"{'TOTAL SANGRIA:':<25} {self.formatar_moeda(data['total_sangria'], False):>20}")
        lines.append(f"{'TOTAL DIFERENÇA:':<25} {self.formatar_moeda(data['total_diferenca'], False):>20}")
        lines.append("=" * line_width)
        
        lines.append("Assinatura: _________________________".center(line_width))
        lines.append(" " * line_width)
        lines.append("Documento interno - Não fiscal".center(line_width))
        
        return "\n".join(lines)
    
    def _limpar_estado_sangria(self):
        """Limpar estado da sangria"""
        atributos = [
            'sangria_ativa', 'sangria_formas', 'sangria_detalhes',
            'sangria_forma_atual', 'modo_sangria_digitar', 'sessao_sangria'
        ]
        
        for attr in atributos:
            if hasattr(self, attr):
                delattr(self, attr)
    
    def cancelar_sangria(self):
        """Cancelar processo de sangria"""
        self._limpar_estado_sangria()
        self.set_display_message("SANGRIA CANCELADA", "", "")
        self.atualizar_modo('funcoes')
        
        
    def modo_suprimento(self):
        """Entrar no modo suprimento"""
        if not hasattr(self, 'usuario_atual'):
            self.set_display_message("ERRO", "FAÇA LOGIN", "")
            return
        
        self.set_display_message(
            "MODO SUPRIMENTO",
            "SELECIONE FORMA DE PAGAMENTO",
            "PARA ADICIONAR VALOR"
        )
        
        self.modo_atual = 'suprimento'
        self.suprimento_detalhes = []
        self.atualizar_botoes_modo()
    
    def processar_suprimento_forma(self, forma_codigo: str):
        """Processar suprimento para forma específica"""
        # Similar à sangria, mas para adicionar valor
        pass
    
    def terminar_suprimento(self):
        """Finalizar suprimento"""
        pass    
        
        
###########sangria fim            
 ###########fecho ini

    def fechar_caixa(self):
        """Fechar caixa atual - VERSÃO COMPLETA"""
        if not hasattr(self, 'usuario_atual'):
            self.set_display_message("ERRO", "FAÇA LOGIN", "")
            return
        
        # Verificar se tem permissão
        if not self.verificar_permissao('fechar_caixa'):
            self.set_display_message(
                "PERMISSÃO NEGADA",
                "SOMENTE GERENTE/SUPERVISOR",
                ""
            )
            return
        
        # Verificar se há sessão aberta
        from session_manager import session_manager
        sessao = session_manager.get_active_session(int(self.pdv_config['pdv_id']))
        
        if not sessao:
            self.set_display_message("ERRO", "CAIXA JÁ FECHADO", "OU NÃO ABERTO")
            return
        
        # Criar janela de fechamento
        self._criar_janela_fechamento_caixa(sessao)
    
    def _criar_janela_fechamento_caixa(self, sessao_data: Dict[str, Any]):
        """Criar janela de fechamento de caixa"""
        janela = tk.Toplevel(self.root)
        janela.title("Fechamento de Caixa")
        janela.geometry("700x600")
        janela.configure(bg=self.cores['fundo_medio'])
        janela.transient(self.root)
        janela.grab_set()
        
        # Centralizar
        janela.update_idletasks()
        width = janela.winfo_width()
        height = janela.winfo_height()
        x = (janela.winfo_screenwidth() // 2) - (width // 2)
        y = (janela.winfo_screenheight() // 2) - (height // 2)
        janela.geometry(f'{width}x{height}+{x}+{y}')
        
        # Título
        tk.Label(janela, text="FECHAMENTO DE CAIXA", 
                bg=self.cores['fundo_medio'], fg=self.cores['texto_primario'],
                font=('Arial', 16, 'bold')).pack(pady=10)
        
        # Frame principal com scroll
        main_frame = tk.Frame(janela, bg=self.cores['fundo_medio'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(main_frame, bg=self.cores['fundo_medio'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.cores['fundo_card'], padx=20, pady=20)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Informações da sessão
        row = 0
        tk.Label(scrollable_frame, text="INFORMAÇÕES DA SESSÃO", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, pady=10, sticky='w')
        row += 1
        
        info_labels = [
            ("Operador:", self.usuario_atual['nome']),
            ("PDV:", f"{self.pdv_config['pdv_id']} - {self.pdv_config['pdv_descricao']}"),
            ("Data Abertura:", sessao_data.get('data_abertura', '').split('T')[0]),
            ("Valor Abertura:", self.formatar_moeda(sessao_data.get('valor_abertura', 0)))
        ]
        
        for label, valor in info_labels:
            tk.Label(scrollable_frame, text=label, 
                    bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                    font=('Arial', 10)).grid(row=row, column=0, sticky='w', pady=2)
            tk.Label(scrollable_frame, text=valor, 
                    bg=self.cores['fundo_card'], fg=self.cores['destaque'],
                    font=('Arial', 10, 'bold')).grid(row=row, column=1, sticky='w', pady=2, padx=(10, 0))
            row += 1
        
        # Separador
        tk.Frame(scrollable_frame, height=2, bg=self.cores['fundo_medio']).grid(
            row=row, column=0, columnspan=3, sticky='ew', pady=10)
        row += 1
        
        # Título valores contados
        tk.Label(scrollable_frame, text="VALORES CONTADOS POR FORMA DE PAGAMENTO", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=3, pady=10, sticky='w')
        row += 1
        
        # Obter formas de pagamento
        from caixa_manager import caixa_manager
        formas = caixa_manager.get_formas_pagamento_com_valor(
            sessao_data['session_id'], 
            int(self.pdv_config['pdv_id'])
        )
        
        self.fechamento_formas = formas
        self.fechamento_entries = {}
        
        # Cabeçalho da tabela
        headers = ["Forma de Pagamento", "Valor Sistema", "Valor Contado", "Diferença"]
        for col, header in enumerate(headers):
            tk.Label(scrollable_frame, text=header, 
                    bg=self.cores['fundo_card'], fg=self.cores['destaque'],
                    font=('Arial', 10, 'bold')).grid(row=row, column=col, pady=5, padx=5)
        row += 1
        
        # Linha separadora
        tk.Frame(scrollable_frame, height=1, bg=self.cores['fundo_medio']).grid(
            row=row, column=0, columnspan=4, sticky='ew', pady=5)
        row += 1
        
        # Linhas para cada forma de pagamento
        for forma in formas:
            # Nome da forma
            tk.Label(scrollable_frame, text=forma['nome'], 
                    bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                    font=('Arial', 10)).grid(row=row, column=0, sticky='w', pady=5, padx=5)
            
            # Valor sistema
            valor_sistema = forma.get('valor_sistema', 0)
            tk.Label(scrollable_frame, text=self.formatar_moeda_sem_simbolo(valor_sistema), 
                    bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                    font=('Arial', 10)).grid(row=row, column=1, pady=5, padx=5)
            
            # Campo para valor contado
            entry_valor = tk.Entry(scrollable_frame, width=12, 
                                  font=('Arial', 10), justify='right')
            entry_valor.insert(0, "0,00")
            entry_valor.grid(row=row, column=2, pady=5, padx=5)
            
            # Campo diferença (readonly)
            label_diferenca = tk.Label(scrollable_frame, text="0,00", 
                                      bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                                      font=('Arial', 10))
            label_diferenca.grid(row=row, column=3, pady=5, padx=5)
            
            # Armazenar referências
            self.fechamento_entries[forma['id']] = {
                'entry': entry_valor,
                'label_diferenca': label_diferenca,
                'valor_sistema': valor_sistema
            }
            
            # Bind para cálculo automático
            entry_valor.bind('<KeyRelease>', 
                           lambda e, fid=forma['id']: self._calcular_diferenca_fechamento(fid))
            
            row += 1
        
        # Separador
        tk.Frame(scrollable_frame, height=2, bg=self.cores['fundo_medio']).grid(
            row=row, column=0, columnspan=4, sticky='ew', pady=10)
        row += 1
        
        # Totais
        tk.Label(scrollable_frame, text="TOTAIS", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 12, 'bold')).grid(row=row, column=0, columnspan=4, pady=10, sticky='w')
        row += 1
        
        # Labels para totais
        self.label_total_sistema = tk.Label(scrollable_frame, text="Sistema: 0,00", 
                                           bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                                           font=('Arial', 10, 'bold'))
        self.label_total_sistema.grid(row=row, column=0, columnspan=2, pady=5, sticky='w')
        
        self.label_total_contado = tk.Label(scrollable_frame, text="Contado: 0,00", 
                                           bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                                           font=('Arial', 10, 'bold'))
        self.label_total_contado.grid(row=row, column=2, columnspan=2, pady=5, sticky='w')
        row += 1
        
        self.label_total_diferenca = tk.Label(scrollable_frame, text="Diferença: 0,00", 
                                             bg=self.cores['fundo_card'], fg='#ff0000',
                                             font=('Arial', 11, 'bold'))
        self.label_total_diferenca.grid(row=row, column=0, columnspan=4, pady=10, sticky='w')
        row += 1
        
        # Observação
        tk.Label(scrollable_frame, text="Observações:", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 10)).grid(row=row, column=0, sticky='w', pady=10)
        row += 1
        
        self.text_observacao = tk.Text(scrollable_frame, height=3, width=50,
                                      font=('Arial', 10))
        self.text_observacao.grid(row=row, column=0, columnspan=4, pady=5, sticky='w')
        row += 1
        
        # Botões
        frame_botoes = tk.Frame(scrollable_frame, bg=self.cores['fundo_card'])
        frame_botoes.grid(row=row, column=0, columnspan=4, pady=20)
        
        btn_calcular = tk.Button(frame_botoes, text="🧮 CALCULAR TOTAIS",
                                bg=self.cores['botao_primario'], fg='white',
                                font=('Arial', 11, 'bold'),
                                width=15, height=2,
                                command=self._calcular_totais_fechamento)
        btn_calcular.pack(side='left', padx=5)
        
        btn_imprimir = tk.Button(frame_botoes, text="🖨️ IMPRIMIR RELATÓRIO",
                                bg=self.cores['alerta'], fg='white',
                                font=('Arial', 11, 'bold'),
                                width=15, height=2,
                                command=lambda: self._imprimir_relatorio_fechamento(janela))
        btn_imprimir.pack(side='left', padx=5)
        
        btn_fechar = tk.Button(frame_botoes, text="✓ FECHAR CAIXA",
                              bg=self.cores['sucesso'], fg='white',
                              font=('Arial', 11, 'bold'),
                              width=15, height=2,
                              command=lambda: self._confirmar_fechamento_caixa(janela, sessao_data))
        btn_fechar.pack(side='left', padx=5)
        
        btn_cancelar = tk.Button(frame_botoes, text="✗ CANCELAR",
                                bg=self.cores['erro'], fg='white',
                                font=('Arial', 11, 'bold'),
                                width=15, height=2,
                                command=janela.destroy)
        btn_cancelar.pack(side='left', padx=5)
        
        # Calcular totais iniciais
        self._calcular_totais_fechamento()
    
    def formatar_moeda_sem_simbolo(self, valor: float) -> str:
        """Formatar valor sem símbolo (para tabelas)"""
        return self.formatar_moeda(valor, show_symbol=False)
    
    def _calcular_diferenca_fechamento(self, forma_id: int):
        """Calcular diferença para uma forma de pagamento"""
        try:
            if forma_id not in self.fechamento_entries:
                return
            
            entry_data = self.fechamento_entries[forma_id]
            valor_contado_str = entry_data['entry'].get().replace(',', '.')
            
            try:
                valor_contado = float(valor_contado_str)
            except ValueError:
                valor_contado = 0.0
            
            valor_sistema = entry_data['valor_sistema']
            diferenca = valor_contado - valor_sistema
            
            # Atualizar label
            cor = '#ff0000' if diferenca < 0 else '#00aa00'
            entry_data['label_diferenca'].config(
                text=f"{diferenca:,.2f}".replace('.', ','),
                fg=cor
            )
            
            # Recalcular totais
            self._calcular_totais_fechamento()
            
        except Exception as e:
            self.logger.error(f"Erro ao calcular diferença: {e}")
    
    def _calcular_totais_fechamento(self):
        """Calcular totais do fechamento"""
        try:
            total_sistema = 0
            total_contado = 0
            
            for forma_id, entry_data in self.fechamento_entries.items():
                total_sistema += entry_data['valor_sistema']
                
                # Obter valor contado
                valor_str = entry_data['entry'].get().replace(',', '.')
                try:
                    valor_contado = float(valor_str)
                except ValueError:
                    valor_contado = 0.0
                
                total_contado += valor_contado
            
            total_diferenca = total_contado - total_sistema
            
            # Atualizar labels
            self.label_total_sistema.config(
                text=f"Sistema: {total_sistema:,.2f}".replace('.', ',')
            )
            self.label_total_contado.config(
                text=f"Contado: {total_contado:,.2f}".replace('.', ',')
            )
            
            # Cor da diferença
            cor_diferenca = '#ff0000' if total_diferenca < 0 else '#00aa00'
            prefixo = "-" if total_diferenca < 0 else "+"
            
            self.label_total_diferenca.config(
                text=f"Diferença: {prefixo}{abs(total_diferenca):,.2f}".replace('.', ','),
                fg=cor_diferenca
            )
            
        except Exception as e:
            self.logger.error(f"Erro ao calcular totais: {e}")
    
    def _imprimir_relatorio_fechamento(self, janela):
        """Imprimir relatório de fechamento"""
        try:
            # Calcular totais
            self._calcular_totais_fechamento()
            
            # Obter dados
            dados_formas = []
            for forma_id, entry_data in self.fechamento_entries.items():
                forma = next((f for f in self.fechamento_formas if f['id'] == forma_id), None)
                if forma:
                    valor_contado_str = entry_data['entry'].get().replace(',', '.')
                    try:
                        valor_contado = float(valor_contado_str)
                    except ValueError:
                        valor_contado = 0.0
                    
                    dados_formas.append({
                        'nome': forma['nome'],
                        'sistema': entry_data['valor_sistema'],
                        'contado': valor_contado,
                        'diferenca': valor_contado - entry_data['valor_sistema']
                    })
            
            # Gerar relatório
            relatorio = self._gerar_relatorio_fechamento(dados_formas)
            
            # Imprimir
            from printer_manager import printer_manager
            
            print_job = {
                'type': 'relatorio_fechamento',
                'text': relatorio,
                'timestamp': time.time()
            }
            
            printer_manager.print_queue.put(print_job)
            
            messagebox.showinfo("Relatório", "Relatório enviado para impressão!")
            
        except Exception as e:
            self.logger.error(f"Erro ao imprimir relatório: {e}")
            messagebox.showerror("Erro", f"Erro ao imprimir: {str(e)}")
    
    def _gerar_relatorio_fechamento(self, dados_formas: List[Dict]) -> str:
        """Gerar texto do relatório de fechamento"""
        from datetime import datetime
        
        lines = []
        line_width = 48
        
        lines.append("=" * line_width)
        lines.append("RELATÓRIO DE FECHAMENTO DE CAIXA".center(line_width))
        lines.append("=" * line_width)
        
        lines.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        lines.append(f"Operador: {self.usuario_atual['nome']}")
        lines.append(f"PDV: {self.pdv_config['pdv_id']} - {self.pdv_config['pdv_descricao']}")
        
        lines.append("-" * line_width)
        lines.append("RESUMO POR FORMA DE PAGAMENTO".center(line_width))
        lines.append("-" * line_width)
        
        lines.append(f"{'Forma':<15} {'Sistema':>10} {'Contado':>10} {'Dif.':>10}")
        lines.append("-" * line_width)
        
        total_sistema = 0
        total_contado = 0
        
        for dado in dados_formas:
            linha = (f"{dado['nome'][:14]:<15} "
                    f"{dado['sistema']:>10.2f} "
                    f"{dado['contado']:>10.2f} "
                    f"{dado['diferenca']:>+10.2f}")
            lines.append(linha)
            
            total_sistema += dado['sistema']
            total_contado += dado['contado']
        
        lines.append("=" * line_width)
        lines.append(f"{'TOTAL SISTEMA:':<25} {total_sistema:>20.2f}")
        lines.append(f"{'TOTAL CONTADO:':<25} {total_contado:>20.2f}")
        
        total_diferenca = total_contado - total_sistema
        cor_sinal = "-" if total_diferenca < 0 else "+"
        lines.append(f"{'DIFERENÇA TOTAL:':<25} {cor_sinal}{abs(total_diferenca):>19.2f}")
        
        lines.append("=" * line_width)
        
        # Observação
        observacao = self.text_observacao.get("1.0", "end-1c").strip()
        if observacao:
            lines.append("Observações:")
            lines.append(observacao[:100])
            lines.append("=" * line_width)
        
        lines.append("Assinatura do Operador:".center(line_width))
        lines.append(" " * line_width)
        lines.append("_________________________".center(line_width))
        lines.append(" " * line_width)
        lines.append("Assinatura do Supervisor:".center(line_width))
        lines.append(" " * line_width)
        lines.append("_________________________".center(line_width))
        lines.append(" " * line_width)
        
        lines.append("Documento interno - Controle de caixa".center(line_width))
        lines.append("=" * line_width)
        
        return "\n".join(lines)
    
    def _confirmar_fechamento_caixa(self, janela, sessao_data: Dict):
        """Confirmar e executar fechamento do caixa"""
        try:
            # Confirmar com o usuário
            resposta = messagebox.askyesno(
                "Confirmar Fechamento",
                "Tem certeza que deseja fechar o caixa?\n"
                "Esta operação não pode ser desfeita."
            )
            
            if not resposta:
                return
            
            # Calcular valores
            valores_contados = {}
            for forma_id, entry_data in self.fechamento_entries.items():
                valor_str = entry_data['entry'].get().replace(',', '.')
                try:
                    valor_contado = float(valor_str)
                except ValueError:
                    valor_contado = 0.0
                
                valores_contados[forma_id] = valor_contado
            
            # Calcular total contado
            total_contado = sum(valores_contados.values())
            
            # Obter observação
            observacao = self.text_observacao.get("1.0", "end-1c").strip()
            
            # Executar fechamento via SessionManager
            from session_manager import session_manager
            
            sucesso = session_manager.close_caixa_session(
                pdv_id=int(self.pdv_config['pdv_id']),
                usuario_id=self.usuario_atual['id'],
                valor_contado=total_contado,
                observacoes=observacao
            )
            
            if sucesso:
                # Registrar detalhes por forma de pagamento
                self._registrar_detalhes_fechamento(sessao_data['session_id'], valores_contados)
                
                # Imprimir relatório final
                self._imprimir_relatorio_fechamento(janela)
                
                # Atualizar interface
                if hasattr(self, 'info_widgets') and len(self.info_widgets) > 4:
                    self.info_widgets[4].config(
                        text="● FECHADO",
                        fg=self.cores['erro']
                    )
                
                # Mostrar mensagem de sucesso
                messagebox.showinfo(
                    "Fechamento Concluído",
                    f"Caixa fechado com sucesso!\n"
                    f"Valor contado: {self.formatar_moeda(total_contado)}"
                )
                
                # Fechar janela
                janela.destroy()
                
                # Mostrar no display
                self.set_display_message(
                    "CAIXA FECHADO",
                    "FECHAMENTO CONCLUÍDO",
                    ""
                )
                
            else:
                messagebox.showerror(
                    "Erro",
                    "Não foi possível fechar o caixa. "
                    "Verifique se há sessão aberta."
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao fechar caixa: {e}")
            messagebox.showerror("Erro", f"Erro ao fechar caixa: {str(e)}")
    
    def _registrar_detalhes_fechamento(self, sessao_id: int, valores_contados: Dict[int, float]):
        """Registrar detalhes do fechamento por forma de pagamento"""
        try:
            from connection_manager import connection_pool
            
            for forma_id, valor_contado in valores_contados.items():
                # Obter valor sistema para esta forma
                query_sistema = """
                SELECT COALESCE(SUM(total_pago), 0) as valor_sistema
                FROM vendas 
                WHERE forma_pagamento_id = %s 
                    AND pdv_id = %s
                    AND DATE(data_emissao) = CURDATE()
                    AND estado = 'EMITIDO'
                """
                
                result = connection_pool.execute_query(
                    query_sistema, 
                    (forma_id, int(self.pdv_config['pdv_id'])), 
                    fetchone=True
                )
                
                valor_sistema = float(result['valor_sistema']) if result else 0.0
                diferenca = valor_contado - valor_sistema
                
                # Inserir detalhe
                query_detalhe = """
                INSERT INTO caixa_fecho_detalhe 
                (sessao_id, forma_pagamento_id, valor_sistema, valor_contado, diferenca)
                VALUES (%s, %s, %s, %s, %s)
                """
                
                connection_pool.execute_query(
                    query_detalhe,
                    (sessao_id, forma_id, valor_sistema, valor_contado, diferenca)
                )
                
        except Exception as e:
            self.logger.error(f"Erro ao registrar detalhes: {e}")
 ## fecho fim 

def main():
    """Função principal"""
    root = tk.Tk()
    
    # Verificar se há conexão
    status = connection_pool.test_connection()
    
    if not status:
        resposta = messagebox.askyesno(
            "Aviso de Conexão",
            "Não foi possível conectar ao banco de dados.\n"
            "Deseja iniciar o sistema em modo offline?"
        )
        
        if not resposta:
            root.destroy()
            return
    
    # Iniciar aplicação
    app = ProfessionalPDV(root)
    root.mainloop()

if __name__ == "__main__":
    main()