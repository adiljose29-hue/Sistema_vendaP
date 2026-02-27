import tkinter as tk
from tkinter import ttk
import datetime

class AdminInterface:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistema PDV - Área Administrativa")
        self.root.geometry("1400x800")
        self.root.configure(bg='#1a1a2e')
        
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
            'botao_secundario': '#a29bfe',
            'menu_ativo': '#e94560'
        }
        
        self.criar_interface()
        
    def criar_interface(self):
        # Frame principal
        main_frame = tk.Frame(self.root, bg=self.cores['fundo_escuro'])
        main_frame.pack(fill='both', expand=True, padx=2, pady=2)
        
        # Cabeçalho
        self.criar_cabecalho(main_frame)
        
        # Área principal dividida
        content_frame = tk.Frame(main_frame, bg=self.cores['fundo_medio'])
        content_frame.pack(fill='both', expand=True, pady=2)
        
        # Menu lateral com scroll
        self.criar_menu_lateral_com_scroll(content_frame)
        
        # Área de conteúdo
        self.content_area = tk.Frame(content_frame, bg=self.cores['fundo_medio'])
        self.content_area.pack(side='right', fill='both', expand=True)
        
        self.mostrar_dashboard()
        
        # Rodapé
        self.criar_rodape(main_frame)
    
    def criar_menu_lateral_com_scroll(self, parent):
        # Frame principal do menu lateral
        menu_outer_frame = tk.Frame(parent, bg=self.cores['fundo_escuro'], width=250)
        menu_outer_frame.pack(side='left', fill='y')
        menu_outer_frame.pack_propagate(False)
        
        # Cabeçalho do menu (fixo)
        menu_header = tk.Frame(menu_outer_frame, bg=self.cores['fundo_card'], height=60)
        menu_header.pack(fill='x', pady=(0, 0))
        menu_header.pack_propagate(False)
        
        tk.Label(menu_header, text="MENU PRINCIPAL", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 12, 'bold')).pack(expand=True)
        
        # Frame para conter o canvas e scrollbar
        menu_container = tk.Frame(menu_outer_frame, bg=self.cores['fundo_escuro'])
        menu_container.pack(fill='both', expand=True)
        
        # Canvas para scrolling
        self.canvas = tk.Canvas(menu_container, bg=self.cores['fundo_escuro'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(menu_container, orient='vertical', command=self.canvas.yview)
        
        # Frame que vai dentro do canvas (onde os menus ficam)
        self.menu_frame = tk.Frame(self.canvas, bg=self.cores['fundo_escuro'])
        
        # Criar window no canvas
        self.canvas_window = self.canvas.create_window((0, 0), window=self.menu_frame, anchor="nw", width=248)
        
        # Configurar canvas e scrollbar
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack dos elementos
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind para redimensionar
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.menu_frame.bind('<Configure>', self._on_frame_configure)
        
        # Bind do mouse wheel para scrolling - CORRIGIDO
        self._bind_mouse_wheel(self.canvas)
        self._bind_mouse_wheel(self.menu_frame)
        self._bind_mouse_wheel(scrollbar)
        
        # Criar os menus
        self.criar_menus()
    
    def _bind_mouse_wheel(self, widget):
        # Bind para Windows e Mac
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel)  # Linux
        widget.bind("<Button-5>", self._on_mousewheel)  # Linux
    
    def _on_mousewheel(self, event):
        # Scrolling com a roda do mouse - CORRIGIDO
        if event.delta:
            # Windows e Mac
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        elif event.num == 4:
            # Linux - scroll up
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            # Linux - scroll down
            self.canvas.yview_scroll(1, "units")
    
    def _on_canvas_configure(self, event):
        # Ajustar a largura do frame interno quando o canvas for redimensionado
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_frame_configure(self, event=None):
        # Atualizar a scrollregion para englobar o frame interno
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def criar_menus(self):
        # Menus principais
        menus = [
            {
                'nome': '📊 DASHBOARD',
                'comando': self.mostrar_dashboard,
                'submenus': []
            },
            {
                'nome': '📁 ARQUIVO',
                'comando': lambda: self.mostrar_conteudo("Arquivo"),
                'submenus': [
                    'Abrir Loja',
                    'Fechar Loja', 
                    'Backup Automático',
                    'Restaurar Backup',
                    'Importar Dados',
                    'Exportar Dados',
                    'Sair do Sistema'
                ]
            },
            {
                'nome': '⚙️ CONFIGURAÇÃO',
                'comando': lambda: self.mostrar_conteudo("Configuração"),
                'submenus': [
                    'Configurações Gerais',
                    'Parametrização do PDV',
                    'Formas de Pagamento',
                    'Impressoras',
                    'Balanças',
                    'Redes',
                    'Segurança'
                ]
            },
            {
                'nome': '💰 VENDAS',
                'comando': lambda: self.mostrar_conteudo("Vendas"),
                'submenus': [
                    'Consulta de Vendas',
                    'Cancelar Venda',
                    'Devoluções',
                    'Orçamentos',
                    'Comandas',
                    'Vendas por Período',
                    'Top Produtos'
                ]
            },
            {
                'nome': '📦 PRODUTOS',
                'comando': lambda: self.mostrar_conteudo("Produtos"),
                'submenus': [
                    'Cadastro de Produtos',
                    'Categorias',
                    'Marcas',
                    'Fornecedores',
                    'Estoque',
                    'Inventário',
                    'Preços e Promoções',
                    'Kits e Combos'
                ]
            },
            {
                'nome': '👥 CLIENTES',
                'comando': lambda: self.mostrar_conteudo("Clientes"),
                'submenus': [
                    'Cadastro de Clientes',
                    'Grupos de Clientes',
                    'Ficha Completa',
                    'Histórico de Compras',
                    'Cartão Fidelidade',
                    'Mensagens SMS/Email'
                ]
            },
            {
                'nome': '🎯 PROMOÇÃO',
                'comando': lambda: self.mostrar_conteudo("Promoção"),
                'submenus': [
                    'Campanhas Ativas',
                    'Criar Promoção',
                    'Descontos Progressivos',
                    'Cupons de Desconto',
                    'Programa Fidelidade',
                    'Promoções por Período'
                ]
            },
            {
                'nome': '👤 USUÁRIOS',
                'comando': lambda: self.mostrar_conteudo("Usuários"),
                'submenus': [
                    'Cadastro de Usuários',
                    'Perfis de Acesso',
                    'Permissões',
                    'Horários de Trabalho',
                    'Comissões',
                    'Relatório de Acessos'
                ]
            },
            {
                'nome': '📈 RELATÓRIOS',
                'comando': lambda: self.mostrar_conteudo("Relatórios"),
                'submenus': [
                    'Relatório de Vendas',
                    'Fluxo de Caixa',
                    'Movimento de Estoque',
                    'Financeiro',
                    'Performance',
                    'Analíticos',
                    'Personalizados'
                ]
            },
            {
                'nome': '📤 EXPORTAÇÃO',
                'comando': lambda: self.mostrar_conteudo("Exportação"),
                'submenus': [
                    'Exportar para Excel',
                    'Exportar para PDF',
                    'Sped Fiscal',
                    'Emitir NFC-e',
                    'Integração Contábil',
                    'API Externa'
                ]
            },
            {
                'nome': '🏦 PRESTAÇÃO',
                'comando': lambda: self.mostrar_conteudo("Prestação de Contas"),
                'submenus': [
                    'Fechamento de Caixa',
                    'Conferência de Valores',
                    'Relatório Gerencial',
                    'Arquivo Magnético',
                    'Demonstrativos',
                    'Auditoria'
                ]
            },
            {
                'nome': '❓ AJUDA',
                'comando': lambda: self.mostrar_conteudo("Ajuda"),
                'submenus': [
                    'Manual do Sistema',
                    'Tutoriais',
                    'Suporte Técnico',
                    'Sobre o Sistema',
                    'Atualizações',
                    'Base de Conhecimento'
                ]
            }
        ]
        
        # Criar os menus
        self.menu_widgets = {}
        for menu in menus:
            self.criar_item_menu(self.menu_frame, menu)
        
        # Atualizar o scrollregion após criar todos os menus
        self.root.update_idletasks()
        self._on_frame_configure()
    
    def criar_item_menu(self, parent, menu):
        menu_frame = tk.Frame(parent, bg=self.cores['fundo_escuro'])
        menu_frame.pack(fill='x', pady=1)
        
        # Botão do menu principal
        btn = tk.Button(menu_frame, 
                       text=menu['nome'],
                       bg=self.cores['fundo_escuro'],
                       fg=self.cores['texto_primario'],
                       font=('Arial', 10, 'bold'),
                       anchor='w',
                       relief='flat',
                       bd=0,
                       padx=20,
                       pady=12,
                       command=lambda m=menu: self.toggle_submenu(m) if menu['submenus'] else menu['comando']())
        btn.pack(fill='x')
        
        # Frame para submenus (inicialmente escondido)
        submenu_frame = tk.Frame(menu_frame, bg=self.cores['fundo_medio'])
        
        # Criar submenus
        for submenu in menu['submenus']:
            sub_btn = tk.Button(submenu_frame,
                              text=f"   {submenu}",
                              bg=self.cores['fundo_medio'],
                              fg=self.cores['texto_secundario'],
                              font=('Arial', 9),
                              anchor='w',
                              relief='flat',
                              bd=0,
                              padx=30,
                              pady=8,
                              command=lambda s=submenu: self.mostrar_conteudo(s))
            sub_btn.pack(fill='x')
            # Bind do mouse wheel nos submenus também
            self._bind_mouse_wheel(sub_btn)
        
        # Armazenar referências
        self.menu_widgets[menu['nome']] = {
            'btn': btn,
            'subframe': submenu_frame,
            'aberto': False,
            'menu_frame': menu_frame
        }
        
        # Bind do mouse wheel no botão do menu
        self._bind_mouse_wheel(btn)
        self._bind_mouse_wheel(menu_frame)
    
    def toggle_submenu(self, menu):
        widget = self.menu_widgets[menu['nome']]
        
        if widget['aberto']:
            widget['subframe'].pack_forget()
            widget['btn'].configure(bg=self.cores['fundo_escuro'])
        else:
            widget['subframe'].pack(fill='x', before=widget['btn'])
            widget['btn'].configure(bg=self.cores['menu_ativo'])
        
        widget['aberto'] = not widget['aberto']
        
        # Atualizar o canvas para ajustar o scrollregion
        self.root.after(100, self._on_frame_configure)

    # ... (o resto dos métodos permanece igual - criar_cabecalho, mostrar_conteudo, mostrar_dashboard, etc.)

    def criar_cabecalho(self, parent):
        header_frame = tk.Frame(parent, bg=self.cores['fundo_card'], height=80)
        header_frame.pack(fill='x', pady=(0, 2))
        header_frame.pack_propagate(False)
        
        # Logo e título
        left_header = tk.Frame(header_frame, bg=self.cores['fundo_card'])
        left_header.pack(side='left', fill='y', padx=20)
        
        tk.Label(left_header, text="FUJITSU ISSXXI", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'], 
                font=('Arial', 20, 'bold')).pack(anchor='w')
        tk.Label(left_header, text="Área Administrativa", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_secundario'], 
                font=('Arial', 12)).pack(anchor='w')
        
        # Informações do usuário
        right_header = tk.Frame(header_frame, bg=self.cores['fundo_card'])
        right_header.pack(side='right', fill='y', padx=20)
        
        user_info = tk.Frame(right_header, bg=self.cores['fundo_card'])
        user_info.pack(side='right', padx=10)
        
        tk.Label(user_info, text="Ana Bela", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'], 
                font=('Arial', 12, 'bold')).pack(anchor='e')
        tk.Label(user_info, text="Administrador", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_secundario'], 
                font=('Arial', 10)).pack(anchor='e')
        
        # Ícone do usuário
        user_icon = tk.Label(right_header, text="👤", 
                           bg=self.cores['fundo_card'], font=('Arial', 20))
        user_icon.pack(side='right', padx=(10, 0))
    
    def mostrar_conteudo(self, titulo):
        # Limpar área de conteúdo
        for widget in self.content_area.winfo_children():
            widget.destroy()
        
        # Título da página
        titulo_frame = tk.Frame(self.content_area, bg=self.cores['fundo_card'], height=60)
        titulo_frame.pack(fill='x', pady=(0, 20))
        titulo_frame.pack_propagate(False)
        
        tk.Label(titulo_frame, text=titulo, 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 16, 'bold')).pack(expand=True)
        
        # Conteúdo específico baseado no título
        if titulo == "Dashboard":
            self.mostrar_dashboard()
        else:
            self.mostrar_padrao(titulo)
    
    def mostrar_dashboard(self):
        # Cards de métricas
        metrics_frame = tk.Frame(self.content_area, bg=self.cores['fundo_medio'])
        metrics_frame.pack(fill='x', pady=10, padx=20)
        
        metrics = [
            ("💰 Vendas Hoje", "Kz 8.518,00", "#00b894", "📈"),
            ("📦 Produtos Vendidos", "23", "#6c5ce7", "📊"),
            ("👥 Clientes Atendidos", "12", "#e94560", "👥"),
            ("🎯 Ticket Médio", "Kz 710,00", "#fdcb6e", "💰")
        ]
        
        for i, (titulo, valor, cor, icone) in enumerate(metrics):
            card = self.criar_card_metricas(metrics_frame, titulo, valor, cor, icone)
            card.grid(row=0, column=i, padx=10, pady=10, sticky='nsew')
            metrics_frame.columnconfigure(i, weight=1)
        
        # Gráficos e informações
        content_grid = tk.Frame(self.content_area, bg=self.cores['fundo_medio'])
        content_grid.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Coluna esquerda - Gráficos
        left_column = tk.Frame(content_grid, bg=self.cores['fundo_medio'])
        left_column.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # Vendas por hora
        vendas_frame = tk.Frame(left_column, bg=self.cores['fundo_card'])
        vendas_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        tk.Label(vendas_frame, text="📊 Vendas por Hora (Hoje)", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 12, 'bold')).pack(anchor='w', padx=15, pady=10)
        
        # Simulação de gráfico
        graf_frame = tk.Frame(vendas_frame, bg='#2c3e50', height=150)
        graf_frame.pack(fill='x', padx=15, pady=(0, 15))
        graf_frame.pack_propagate(False)
        
        tk.Label(graf_frame, text="Gráfico de Vendas por Hora\n(Implementar com matplotlib)", 
                bg='#2c3e50', fg=self.cores['texto_secundario'], font=('Arial', 10)).pack(expand=True)
        
        # Produtos mais vendidos
        produtos_frame = tk.Frame(left_column, bg=self.cores['fundo_card'])
        produtos_frame.pack(fill='both', expand=True)
        
        tk.Label(produtos_frame, text="🏆 Top Produtos (Mês)", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 12, 'bold')).pack(anchor='w', padx=15, pady=10)
        
        # Lista de produtos
        produtos = [
            ("OVOS CARTAD 30UN", "45 unidades"),
            ("MASSA MEADA NACIONAL", "32 unidades"),
            ("ARROZ BRANCO 5KG", "28 unidades"),
            ("LEITE UHT 1L", "25 unidades"),
            ("AÇÚCAR 1KG", "22 unidades")
        ]
        
        for produto, qtd in produtos:
            prod_item = tk.Frame(produtos_frame, bg=self.cores['fundo_card'])
            prod_item.pack(fill='x', padx=15, pady=2)
            
            tk.Label(prod_item, text=produto, bg=self.cores['fundo_card'],
                    fg=self.cores['texto_primario'], font=('Arial', 9)).pack(side='left')
            tk.Label(prod_item, text=qtd, bg=self.cores['fundo_card'],
                    fg=self.cores['texto_secundario'], font=('Arial', 9)).pack(side='right')
        
        # Coluna direita - Alertas e informações
        right_column = tk.Frame(content_grid, bg=self.cores['fundo_medio'], width=300)
        right_column.pack(side='right', fill='y', padx=(10, 0))
        right_column.pack_propagate(False)
        
        # Alertas do sistema
        alertas_frame = tk.Frame(right_column, bg=self.cores['fundo_card'])
        alertas_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(alertas_frame, text="⚠️ ALERTAS DO SISTEMA", 
                bg=self.cores['fundo_card'], fg=self.cores['alerta'],
                font=('Arial', 12, 'bold')).pack(anchor='w', padx=15, pady=10)
        
        alertas = [
            ("Estoque baixo: OVOS CARTAD 30UN", "5 unidades"),
            ("Backup pendente", "2 dias"),
            ("Atualização disponível", "v2.1.5")
        ]
        
        for alerta, info in alertas:
            alert_item = tk.Frame(alertas_frame, bg=self.cores['fundo_card'])
            alert_item.pack(fill='x', padx=15, pady=5)
            
            tk.Label(alert_item, text=alerta, bg=self.cores['fundo_card'],
                    fg=self.cores['texto_primario'], font=('Arial', 9)).pack(anchor='w')
            tk.Label(alert_item, text=info, bg=self.cores['fundo_card'],
                    fg=self.cores['texto_secundario'], font=('Arial', 8)).pack(anchor='w')
        
        # Informações rápidas
        info_frame = tk.Frame(right_column, bg=self.cores['fundo_card'])
        info_frame.pack(fill='both', expand=True)
        
        tk.Label(info_frame, text="ℹ️ INFORMAÇÕES RÁPIDAS", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                font=('Arial', 12, 'bold')).pack(anchor='w', padx=15, pady=10)
        
        infos = [
            ("Caixas ativos", "3"),
            ("Vendas do mês", "Kz 125.840,00"),
            ("Clientes cadastrados", "156"),
            ("Produtos ativos", "245")
        ]
        
        for info, valor in infos:
            info_item = tk.Frame(info_frame, bg=self.cores['fundo_card'])
            info_item.pack(fill='x', padx=15, pady=3)
            
            tk.Label(info_item, text=info, bg=self.cores['fundo_card'],
                    fg=self.cores['texto_secundario'], font=('Arial', 9)).pack(side='left')
            tk.Label(info_item, text=valor, bg=self.cores['fundo_card'],
                    fg=self.cores['texto_primario'], font=('Arial', 9, 'bold')).pack(side='right')
    
    def criar_card_metricas(self, parent, titulo, valor, cor, icone):
        card = tk.Frame(parent, bg=self.cores['fundo_card'], relief='raised', bd=1)
        
        # Header do card
        header = tk.Frame(card, bg=cor, height=30)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text=icone, bg=cor, fg='white',
                font=('Arial', 12)).pack(side='left', padx=10)
        tk.Label(header, text=titulo, bg=cor, fg='white',
                font=('Arial', 10, 'bold')).pack(side='left', padx=5)
        
        # Conteúdo do card
        content = tk.Frame(card, bg=self.cores['fundo_card'])
        content.pack(fill='both', expand=True, padx=15, pady=15)
        
        tk.Label(content, text=valor, bg=self.cores['fundo_card'],
                fg=self.cores['texto_primario'], font=('Arial', 18, 'bold')).pack()
        
        return card
    
    def mostrar_padrao(self, titulo):
        content_frame = tk.Frame(self.content_area, bg=self.cores['fundo_medio'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        tk.Label(content_frame, text=f"Página: {titulo}", 
                bg=self.cores['fundo_medio'], fg=self.cores['texto_primario'],
                font=('Arial', 14)).pack(expand=True)
        
        tk.Label(content_frame, text="Conteúdo específico será implementado aqui", 
                bg=self.cores['fundo_medio'], fg=self.cores['texto_secundario'],
                font=('Arial', 12)).pack(expand=True)
    
    def criar_rodape(self, parent):
        rodape_frame = tk.Frame(parent, bg=self.cores['fundo_card'], height=30)
        rodape_frame.pack(fill='x', pady=(2, 0))
        rodape_frame.pack_propagate(False)
        
        # Data e hora
        self.label_data_hora = tk.Label(rodape_frame, text="", 
                                       bg=self.cores['fundo_card'], fg=self.cores['texto_primario'],
                                       font=('Arial', 9))
        self.label_data_hora.pack(side='left', padx=15)
        self.atualizar_data_hora()
        
        # Status
        tk.Label(rodape_frame, text="● SISTEMA OPERACIONAL", 
                bg=self.cores['fundo_card'], fg=self.cores['sucesso'],
                font=('Arial', 9, 'bold')).pack(side='right', padx=15)
        
        # Versão
        tk.Label(rodape_frame, text="v2.1.4 | Fujitsu ISSXXI", 
                bg=self.cores['fundo_card'], fg=self.cores['texto_secundario'],
                font=('Arial', 9)).pack(side='right', padx=15)
    
    def atualizar_data_hora(self):
        agora = datetime.datetime.now()
        data_hora_str = agora.strftime("%d/%m/%Y %H:%M:%S")
        self.label_data_hora.config(text=data_hora_str)
        self.root.after(1000, self.atualizar_data_hora)

def main():
    root = tk.Tk()
    app = AdminInterface(root)
    root.mainloop()

if __name__ == "__main__":
    main()