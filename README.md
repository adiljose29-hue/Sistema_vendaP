# Sistema_vendaP
Sistems de venda
o sistema de venda tem esta estrutura 
PDV_System/
│
├──
├── POS.py                     # Interface do Ponto de Venda
├── AdmiG.py                   # Interface Administrativa
├── config.ini                 # Configurações gerais do sistema
├── recibo_config.ini          # Configurações do recibo
├── database.py                # Gerenciador de banco de dados
├── connection_manager.py      # Gerenciador de conexões otimizado
├── config_manager.py          # Gerenciador de configurações
├── printer_manager.py         # Gerenciador de impressão
├── auth_manager.py            # Gerenciador de autenticação
├── product_cache.py           # Cache inteligente de produtos
├── mode_manager.py            # Gerenciador de modos de operação
├── key_processor.py           # Processador de teclas otimizado
├── log_manager.py             # Sistema de logs e monitoramento
├── fiscal_manager.py          # Gerenciador fiscal (AGT)
├── receipt_generator.py       # Gerador de recibos
├── currency_formatter.py      # Formatador de moeda (Kz)
├── session_manager.py         # Gerenciador de sessões
├── data_validator.py          # Validador de dados
│
└── logs/                      # Pasta de logs
    ├── system.log
    ├── sales.log
    └── errors.log
