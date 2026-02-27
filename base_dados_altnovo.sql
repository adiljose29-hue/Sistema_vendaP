CREATE DATABASE pdv_sge5 ;
USE pdv_sge5;

CREATE TABLE empresa (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nif VARCHAR(20) NOT NULL,
    nome VARCHAR(200) NOT NULL,
    nome_comercial VARCHAR(200),
    endereco TEXT,
    cidade VARCHAR(100),
    pais VARCHAR(50) DEFAULT 'Angola',
	atividade_principal VARCHAR(200),
    codigo_postal VARCHAR(20),
    municipio VARCHAR(100),
    provincia VARCHAR(100),
    telefone VARCHAR(50),
    email VARCHAR(100),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE loja (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id INT NOT NULL,
    codigo CHAR(4) NOT NULL, -- 0001, 0002
    nome VARCHAR(100),
    endereco TEXT,
    ativo BOOLEAN DEFAULT 1,
    FOREIGN KEY (empresa_id) REFERENCES empresa(id));

CREATE TABLE pdv (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loja_id INT NOT NULL,
    codigo CHAR(3) NOT NULL, -- 001, 002
	numero int NOT NULL,
    descricao VARCHAR(100),
    ativo BOOLEAN DEFAULT 1,
    FOREIGN KEY (loja_id) REFERENCES loja(id));

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
	loja_id int DEFAULT NULL,
    numero_trabalhador int NOT NULL UNIQUE,
    nome VARCHAR(100),
    username VARCHAR(50),
    senha VARCHAR(10),
    perfil ENUM('gerente','admin','operador','supervisor') DEFAULT 'operador',
	per_venda enum('0','1') DEFAULT '1',-- 0 - venda não , 1 - venda sim
    ativo BOOLEAN DEFAULT 1,
	FOREIGN KEY (loja_id) REFERENCES loja(id));

CREATE TABLE forma_pagamento (
    id INT AUTO_INCREMENT PRIMARY KEY,
	loja_id int DEFAULT NULL,
	nome varchar(50) NOT NULL,
	codigo varchar(10) NOT NULL,
    aceita_troco tinyint(1) DEFAULT '0',
    limite_pagamento DECIMAL(18,2) DEFAULT 0,
	tipo_sangria enum('0','1') DEFAULT '1',-- 0 - automática , 1 - manual
	digitar_valor tinyint(1) DEFAULT '0',
	ativo tinyint(1) DEFAULT '1',
	FOREIGN KEY (loja_id) REFERENCES loja(id));

INSERT INTO `forma_pagamento` (`id`, `loja_id`, `nome`, `codigo`, `aceita_troco`, `limite_pagamento`, `tipo_sangria`, `ativo`) VALUES
(1, 1, 'Dinheiro', 'DIN', 1, 0.00, '0', 1),
(2, 1, 'Multicaixa', 'MC', 0, 0.00, '1', 1),
(3, 1, 'Cartão de Crédito', 'CC', 0, 0.00, '1', 1),
(4, 1, 'Cartão de Débito', 'CD', 0, 0.00, '1', 1),
(5, 1, 'Cartão CLIENTE', 'CL', 0, 0.00, '1', 1);

CREATE TABLE loja_sessao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loja_id INT NOT NULL,
    data_abertura DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_fecho DATETIME,
    usuario_abertura_id INT,
    usuario_fecho_id INT,
    estado ENUM('ABERTA','FECHADA','Manutencao') DEFAULT 'ABERTA',
    observacao VARCHAR(255),
    FOREIGN KEY (loja_id) REFERENCES loja(id),
    FOREIGN KEY (usuario_abertura_id) REFERENCES usuarios(id),
    FOREIGN KEY (usuario_fecho_id) REFERENCES usuarios(id));

CREATE TABLE caixa_sessao (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loja_sessao_id INT NOT NULL,
    pdv_id INT NOT NULL,
    usuario_id INT NOT NULL,
    data_abertura DATETIME DEFAULT CURRENT_TIMESTAMP,
    data_fecho DATETIME,
    valor_abertura DECIMAL(18,2) NOT NULL,
	valor_fecho DECIMAL(18,2),
    total_vendas DECIMAL(18,2) DEFAULT 0,
    total_devolucoes DECIMAL(18,2) DEFAULT 0,
    total_sangrias DECIMAL(18,2) DEFAULT 0,
    total_reforcos DECIMAL(18,2) DEFAULT 0,
    valor_teorico DECIMAL(18,2),
    valor_contado DECIMAL(18,2),
    diferenca DECIMAL(18,2),
    estado ENUM('ABERTA','FECHADA','Manutencao') DEFAULT 'ABERTA',
    FOREIGN KEY (loja_sessao_id) REFERENCES loja_sessao(id),
    FOREIGN KEY (pdv_id) REFERENCES pdv(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id));

CREATE TABLE caixa_movimentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sessao_id INT NOT NULL,
    tipo ENUM('SANGRIA','REFORCO'),
    valor DECIMAL(18,2),
    motivo VARCHAR(255),
	usuario_id INT NOT NULL,
	pdv_id INT NOT NULL,
	forma_pagamento_id INT,
    data_movimento DATETIME DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (pdv_id) REFERENCES pdv(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
	FOREIGN KEY (forma_pagamento_id) REFERENCES forma_pagamento(id),
    FOREIGN KEY (sessao_id) REFERENCES caixa_sessao(id));

CREATE TABLE caixa_fecho_detalhe (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sessao_id INT NOT NULL,
    forma_pagamento_id INT,
    valor_sistema DECIMAL(18,2),
    valor_contado DECIMAL(18,2),
    diferenca DECIMAL(18,2),
	created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (forma_pagamento_id) REFERENCES forma_pagamento(id),
    FOREIGN KEY (sessao_id) REFERENCES caixa_sessao(id));


CREATE TABLE clientes (
    id INT AUTO_INCREMENT PRIMARY KEY,
	loja_id INT NOT NULL,
    nif VARCHAR(20),
    nome VARCHAR(200),
    endereco TEXT,
    telefone VARCHAR(50),
    email VARCHAR(100),
	tipo_cliente enum('Consumidor Final','Sujeito Passivo', 'contribuinte', 'isento') DEFAULT 'Consumidor Final',
	saldo_pontos INT DEFAULT 0,
	endereco_fiscal TEXT,
    provincia VARCHAR(100),
    municipio VARCHAR(100),
    bairro VARCHAR(100),
    rua VARCHAR(100),
    codigo_postal VARCHAR(20), 
	ativo tinyint(1) DEFAULT '1',
	created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
	UNIQUE KEY `nif` (`nif`),
	FOREIGN KEY (loja_id) REFERENCES loja(id));

CREATE TABLE taxa (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(10) NOT NULL UNIQUE,   -- ex: IVA14, IVA7, ISENTO
    descricao VARCHAR(100) NOT NULL,
    percentagem DECIMAL(5,2) NOT NULL,    -- ex: 14.00
    tipo ENUM('IVA','ISENTO','OUTRO') NOT NULL,
	lett VARCHAR(2) NOT NULL DEFAULT 'H',
    ativo BOOLEAN DEFAULT TRUE);

INSERT INTO `taxa` (`id`, `codigo`, `descricao`, `percentagem`, `tipo`, `lett`, `ativo`) VALUES
(1, 'IVA_NOR', 'IVA Taxa Normal', 14.00, 'IVA', 'A', 1),
(2, 'IVA_RED', 'IVA Taxa Reduzida', 7.00, 'IVA', 'C', 1),
(3, 'IVA_ISE', 'IVA Isento', 0.00, 'ISENTO', 'H', 1),
(4, 'IS', 'Imposto de Selo', 1.00, 'OUTRO', 'D', 1);

CREATE TABLE IF NOT EXISTS categorias (
   id int AUTO_INCREMENT PRIMARY KEY,
   nome varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
   descricao text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
   ativo tinyint(1) DEFAULT '1') ;

INSERT INTO categorias (`id`, `nome`, `descricao`, `ativo`) VALUES
(1,  'Alimentação', 'Produtos alimentares', 1),
(2,  'Bebidas', 'Bebidas diversas', 1),
(3,  'Limpeza', 'Produtos de limpeza', 1),
(4,  'Higiene', 'Produtos de higiene pessoal', 1),
(5, 'Padaria', 'Produtos de padaria', 1),
(6,  'Talho', 'Produtos de talho', 1);

CREATE TABLE produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
	loja_id int DEFAULT NULL,
	categoria_id int DEFAULT NULL,
	fornecedor_id int DEFAULT NULL,
	codigo_interno int ,
	codigo VARCHAR(50) UNIQUE,
    descricao VARCHAR(200),
    tipo ENUM('UNIDADE','PESO','SERVICO'),
	unidade_medida enum('UN','KG') DEFAULT 'UN',
	preco_venda DECIMAL(18,2),
	preco_custo decimal(12,2) DEFAULT '0.00',
	letra_iva CHAR(1) NULL,
    taxa_id INT NOT NULL,
	stock_minimo decimal(10,3) DEFAULT '0.000',
	stock_maximo decimal(10,3) DEFAULT '0.000',
    stock_atual decimal(10,3) DEFAULT '0.000',
    stock_reservado decimal(10,3) DEFAULT '0.000',
	regime_especial_id INT NULL,
	motivo_isencao_id INT NULL,
	localizacao_armazem varchar(100) DEFAULT NULL,
	created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT 1,
	FOREIGN KEY (motivo_isencao_id) REFERENCES motivos_isencao_iva(id),
    FOREIGN KEY (regime_especial_id) REFERENCES regimes_especiais_iva(id),
	FOREIGN KEY (loja_id) REFERENCES loja(id),
	FOREIGN KEY (fornecedor_id) REFERENCES fornecedores(id),
	FOREIGN KEY (categoria_id) REFERENCES categorias(id),
	FOREIGN KEY (taxa_id) REFERENCES taxa(id));
	
CREATE TABLE IF NOT EXISTS fornecedores (
    id INT PRIMARY KEY AUTO_INCREMENT,
    loja_id INT NOT NULL,
    codigo_fornecedor VARCHAR(20) UNIQUE NOT NULL,
    nome VARCHAR(255) NOT NULL,
    nif VARCHAR(20) UNIQUE,
    endereco TEXT,
    telefone VARCHAR(20),
    email VARCHAR(255),
    website VARCHAR(255),
    contacto_nome VARCHAR(255),
    contacto_telefone VARCHAR(20),
    contacto_email VARCHAR(255),
    prazo_entrega_dias INT DEFAULT 0,
    condicoes_pagamento VARCHAR(100),
    moeda VARCHAR(3) DEFAULT 'AOA',
    iban VARCHAR(34),
    swift VARCHAR(11),
    numero_conta VARCHAR(50),
    observacoes TEXT,
    ativo BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (loja_id) REFERENCES lojas(id) ON DELETE CASCADE,
    INDEX idx_fornecedor_loja (loja_id),
    INDEX idx_fornecedor_nif (nif)
);	
	
INSERT INTO `fornecedores` (`id`, `loja_id`, `codigo_fornecedor`, `nome`, `nif`, `endereco`, `telefone`, `email`, `website`, `contacto_nome`, `contacto_telefone`, `contacto_email`, `prazo_entrega_dias`, `condicoes_pagamento`, `moeda`, `iban`, `swift`, `numero_conta`, `observacoes`, `ativo`, `created_at`, `updated_at`) VALUES
(1, 1, 'FOR001', 'Distribuidora Angola Lda', '500012345', 'Rua do Comércio, 123, Luanda', '+244 222 123 456', 'geral@distribuidora.co.ao', NULL, 'João Silva', '+244 923 456 789', NULL, 3, '30 dias', 'AOA', 'AO06012345678901234567890', 'BICXXXX', NULL, NULL, 1, '2026-02-18 07:33:01', '2026-02-18 07:33:01'),
(2, 1, 'FOR002', 'Bebidas e Cia', '500067890', 'Avenida Industrial, 45, Viana', '+244 222 789 012', 'compras@bebidasecia.co.ao', NULL, 'Maria Santos', '+244 924 567 890', NULL, 2, '15 dias', 'AOA', 'AO06009876543210987654321', 'BICYYYY', NULL, NULL, 1, '2026-02-18 07:33:01', '2026-02-18 07:33:01'),
(3, 1, 'FOR003', 'Produtos de Limpeza Lda', '500034567', 'Zona Económica, Lote 8, Viana', '+244 222 345 678', 'vendas@limpeza.co.ao', NULL, 'Pedro Costa', '+244 925 678 901', NULL, 5, '30 dias', 'AOA', 'AO06056789012345678901234', 'BICZZZZ', NULL, NULL, 1, '2026-02-18 07:33:01', '2026-02-18 07:33:01'),
(4, 1, 'FOR004', 'Distribuidora de Alimentos SA', '500078901', 'Mercado Grossista, Loja 15, Luanda', '+244 222 901 234', 'geral@alimentos.co.ao', NULL, 'Ana Paula', '+244 926 789 012', NULL, 2, '7 dias', 'AOA', 'AO06012345678901234567890', 'BICAAAA', NULL, NULL, 1, '2026-02-18 07:33:01', '2026-02-18 07:33:01'),
(5, 1, 'FOR005', 'Talhos Central', '500045678', 'Rua do Mercado, 78, Maianga', '+244 222 567 890', 'encomendas@talhos.co.ao', NULL, 'Carlos Ferreira', '+244 927 890 123', NULL, 1, 'Pronto pagamento', 'AOA', NULL, NULL, NULL, NULL, 1, '2026-02-18 07:33:01', '2026-02-18 07:33:01');
	

CREATE TABLE IF NOT EXISTS tipos_documento (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(5) NOT NULL,   -- FT, FS, FR, NC, ND, CO
    nome VARCHAR(50) NOT NULL,
    descricao TEXT);

CREATE TABLE sequencias_vendas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loja_id INT NOT NULL,
    pdv_id INT NULL,  -- NULL = sequência por loja
    tipo_venda ENUM('FT','FR','FS','NC','ND','CO') NOT NULL,
    ano INT NOT NULL,
    ultimo_numero INT NOT NULL DEFAULT 0,
    data_ultima_emissao DATETIME,
    UNIQUE (loja_id, pdv_id, tipo_venda, ano),
    FOREIGN KEY (loja_id) REFERENCES loja(id),
    FOREIGN KEY (pdv_id) REFERENCES pdvs(id));

CREATE TABLE vendas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id INT NOT NULL,
    loja_id INT NOT NULL,
    pdv_id INT NOT NULL,
	usuario_id INT NOT NULL,
    cliente_id INT,
	numero_venda BIGINT NOT NULL UNIQUE,
    tipo enum('FT','FR','FS','NC','ND') DEFAULT NULL,
    numero_documento VARCHAR(50) UNIQUE,
	taxa_id INT NOT NULL,
	valor_iva DECIMAL(18,2),
    total_sem_iva DECIMAL(18,2),
    total_iva DECIMAL(18,2),
    total_com_iva DECIMAL(18,2),
	serie VARCHAR(5) DEFAULT 'A',
	estado ENUM('NORMAL','RASCUNHO','EMITIDO','ANULADO') DEFAULT 'EMITIDO',
	forma_pagamento_id INT NOT NULL,
	total_venda DECIMAL(18,2) DEFAULT 0,
	total_pago DECIMAL(18,2) DEFAULT 0,
    troco DECIMAL(18,2) DEFAULT 0,
    venda_origem_id INT, -- NC / ND / Devolução
	numero_assinatura varchar(100) DEFAULT NULL,
	codigo_moeda VARCHAR(3) DEFAULT 'AOA',
	taxa_cambio DECIMAL(10,4) DEFAULT 1, 
	hash_control VARCHAR(155),
	hash_assinatura VARCHAR(155),
    system_entry_date DATETIME NOT NULL,
    source_id INT NOT NULL,
	data_anulacao date DEFAULT NULL,
	atcud VARCHAR(50) NULL,
	qr_code TEXT,
    hash_documento VARCHAR(155),
	desconto_global DECIMAL(18,2) DEFAULT 0,
    total_desconto DECIMAL(18,2) DEFAULT 0,
	preco_original DECIMAL(18,2),
    desconto_percentual DECIMAL(5,2),
    total_sem_desconto DECIMAL(10,2),
    total_liquido DECIMAL(18,2),
	tipo_desconto VARCHAR(50),
	data_emissao DATETIME NOT NULL,
	created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresa(id),
    FOREIGN KEY (loja_id) REFERENCES loja(id),
    FOREIGN KEY (pdv_id) REFERENCES pdv(id),
	FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
	FOREIGN KEY (forma_pagamento_id) REFERENCES forma_pagamento(id),
	FOREIGN KEY (source_id) REFERENCES usuarios(id),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id));

CREATE TABLE venda_itens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    venda_id INT NOT NULL,
    produto_id INT NOT NULL,
    descricao VARCHAR(200),
    quantidade DECIMAL(18,3),
    preco_unitario DECIMAL(18,2),
    total DECIMAL(18,2),
    taxa_iva DECIMAL(5,2),
	preco_original DECIMAL(18,2),
    desconto_percentual DECIMAL(5,2),
    desconto_valor DECIMAL(18,2),
    total_desconto DECIMAL(18,2),
    total_liquido DECIMAL(18,2),
	tipo_desconto VARCHAR(50),
	created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (venda_id) REFERENCES vendas(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id));

CREATE TABLE pagamentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    venda_id INT NOT NULL,
    metodo ENUM('DINHEIRO','TPA','TRANSFERENCIA','OUTRO') NOT NULL,
    total_venda DECIMAL(18,2) DEFAULT 0,
	total_pago DECIMAL(18,2) DEFAULT 0,
    troco DECIMAL(18,2) DEFAULT 0,
    sessao_id INT,
    pdv_id INT,
    usuario_id INT,
	forma_pagamento_id int DEFAULT NULL,
	estado varchar(20),
    data_pagamento DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (venda_id) REFERENCES vendas(id),
    FOREIGN KEY (sessao_id) REFERENCES caixa_sessao(id),
    FOREIGN KEY (pdv_id) REFERENCES pdv(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
	FOREIGN KEY (forma_pagamento_id) REFERENCES forma_pagamento(id));

CREATE TABLE hash_fiscal (
id INT AUTO_INCREMENT PRIMARY KEY,
venda_id INT NOT NULL,
hash_atual CHAR(40) NOT NULL,
hash_anterior CHAR(40),
data_geracao DATETIME NOT NULL,
FOREIGN KEY (venda_id) REFERENCES vendas(id));

CREATE TABLE stock (
    id INT AUTO_INCREMENT PRIMARY KEY,
    produto_id INT NOT NULL,
    loja_id INT NOT NULL,
    quantidade DECIMAL(18,3) DEFAULT 0,
    UNIQUE (produto_id, loja_id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id),
    FOREIGN KEY (loja_id) REFERENCES loja(id));

CREATE TABLE stock_movimentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    produto_id INT NOT NULL,
    loja_id INT NOT NULL,
	tipo_movimento ENUM('entrada_compra','entrada_devolucao_cliente','entrada_transferencia','entrada_ajuste','saida_venda','saida_devolucao_fornecedor','saida_transferencia','saida_ajuste','saida_quebra','inventario_inicial') DEFAULT NULL,
    documento_tipo VARCHAR(20), -- 'venda', 'compra', 'devolucao', etc
	documento_id INT, -- ID do documento relacionado (vendas.id, compras.id, devolucoes.id)
    documento_numero VARCHAR(50), -- Número do documento para referência rápida
	quantidade DECIMAL(18,3),
    venda_id INT,       -- FT / NC / ND / etc
    sessao_id INT,          -- caixa aberto
    pdv_id INT,
    usuario_id INT,
    origem VARCHAR(50),     -- VENDA, DEVOLUCAO, INVENTARIO
    observacao VARCHAR(255),
	stock_anterior DECIMAL(10,3) NOT NULL,
    stock_posterior DECIMAL(10,3) NOT NULL,
    custo_unitario DECIMAL(10,2),
    custo_total DECIMAL(10,2),
    observacoes TEXT,
    data_movimento DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (produto_id) REFERENCES produtos(id),
    FOREIGN KEY (loja_id) REFERENCES loja(id),
    FOREIGN KEY (venda_id) REFERENCES vendas(id),
    FOREIGN KEY (sessao_id) REFERENCES caixa_sessao(id),
    FOREIGN KEY (pdv_id) REFERENCES pdv(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id));

CREATE TABLE documento_status (
id INT AUTO_INCREMENT PRIMARY KEY,
venda_id INT NOT NULL,
usuario_id INT,
estado ENUM('N','A','P','T') NOT NULL,
motivo_anulacao VARCHAR(255),
data_estado DATETIME NOT NULL,
FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
FOREIGN KEY (venda_id) REFERENCES vendas(id));

CREATE INDEX idx_vendas_emissao ON vendas(data_emissao);
CREATE INDEX idx_vendas_documento ON vendas(numero_documento);
CREATE INDEX idx_vendas_cliente ON vendas(cliente_id);
CREATE INDEX idx_stock_produto ON stock(produto_id, loja_id);

CREATE TABLE IF NOT EXISTS `desconto_progressivo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `promocao_id` int NOT NULL,
  `valor_minimo` decimal(18,2) NOT NULL,
  `valor_maximo` decimal(18,2) DEFAULT NULL,
  `desconto_percentual` decimal(5,2) NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `promocao_id` (`promocao_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `promocao_aplicada` (
  `id` int NOT NULL AUTO_INCREMENT,
  `venda_id` int NOT NULL,
  `promocao_id` int NOT NULL,
  `produto_id` int DEFAULT NULL,
  `cliente_id` int DEFAULT NULL,
  `valor_desconto` decimal(18,2) NOT NULL,
  `percentual_desconto` decimal(5,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `venda_id` (`venda_id`),
  KEY `promocao_id` (`promocao_id`),
  KEY `produto_id` (`produto_id`),
  KEY `cliente_id` (`cliente_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


CREATE TABLE IF NOT EXISTS `promocao_categorias` (
  `id` int NOT NULL AUTO_INCREMENT,
  `promocao_id` int NOT NULL,
  `categoria_id` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `promocao_id` (`promocao_id`,`categoria_id`),
  KEY `categoria_id` (`categoria_id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `promocao_categorias` (`id`, `promocao_id`, `categoria_id`, `created_at`) VALUES
(1, 1, 1, '2026-02-05 16:31:55');

CREATE TABLE IF NOT EXISTS `promocao_clientes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `promocao_id` int NOT NULL,
  `cliente_id` int NOT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `promocao_id` (`promocao_id`,`cliente_id`),
  KEY `cliente_id` (`cliente_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `promocao_combos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `promocao_id` int NOT NULL,
  `produto_id` int NOT NULL,
  `quantidade_combo` decimal(10,3) NOT NULL,
  `preco_combo` decimal(18,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `promocao_id` (`promocao_id`),
  KEY `produto_id` (`produto_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `promocao_produtos` (
  `id` int NOT NULL AUTO_INCREMENT,
  `promocao_id` int NOT NULL,
  `produto_id` int NOT NULL,
  `loja_id` int DEFAULT NULL,
  `quantidade_minima` decimal(10,3) DEFAULT '1.000',
  `desconto_adicional` decimal(5,2) DEFAULT '0.00',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `promocao_id` (`promocao_id`,`produto_id`),
  KEY `produto_id` (`produto_id`),
  KEY `loja_id` (`loja_id`)
) ENGINE=MyISAM AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `promocao_produtos` (`id`, `promocao_id`, `produto_id`, `loja_id`, `quantidade_minima`, `desconto_adicional`, `created_at`) VALUES
(1, 2, 3, 1, 2.000, 0.00, '2026-02-05 16:31:55');

CREATE TABLE IF NOT EXISTS `promocoes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `codigo` varchar(20) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `descricao` text,
  `tipo_promocao_id` int NOT NULL,
  `data_inicio` date NOT NULL,
  `data_fim` date NOT NULL,
  `hora_inicio` time DEFAULT '08:00:00',
  `hora_fim` time DEFAULT '20:00:00',
  `valor_fixo` decimal(18,2) DEFAULT NULL,
  `percentual` decimal(5,2) DEFAULT NULL,
  `compra_minima` decimal(18,2) DEFAULT NULL,
  `leva_gratis_qtd` int DEFAULT NULL,
  `ativo` tinyint(1) DEFAULT '1',
  `aplicavel_em` varchar(20) DEFAULT 'PRODUTO',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`),
  KEY `tipo_promocao_id` (`tipo_promocao_id`)
) ENGINE=MyISAM AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `promocoes` (`id`, `codigo`, `nome`, `descricao`, `tipo_promocao_id`, `data_inicio`, `data_fim`, `hora_inicio`, `hora_fim`, `valor_fixo`, `percentual`, `compra_minima`, `leva_gratis_qtd`, `ativo`, `aplicavel_em`, `created_at`, `updated_at`) VALUES
(1, 'PROMO_TESTE_1', 'Desconto 10% Alimentação', '10% desconto em produtos de alimentação', 7, '2025-12-01', '2026-02-18', '08:00:00', '20:00:00', NULL, 10.00, NULL, NULL, 1, 'CATEGORIA', '2026-02-05 16:31:55', '2026-02-05 17:10:32'),
(2, 'PROMO_TESTE_2', 'Compre 2 Leve 3', 'Na compra de 2 unidades leve 3', 3, '2025-12-01', '2025-12-31', '08:00:00', '20:00:00', NULL, NULL, NULL, NULL, 1, 'PRODUTO', '2026-02-05 16:31:55', '2026-02-05 16:31:55');


CREATE TABLE IF NOT EXISTS `tipos_promocao` (
  `id` int NOT NULL AUTO_INCREMENT,
  `codigo` varchar(20) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `descricao` text,
  `ativo` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `codigo` (`codigo`)
) ENGINE=MyISAM AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS venda_itens_promocoes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    venda_item_id INT NOT NULL,
    promocao_id INT,
    nome_promocao VARCHAR(255) NOT NULL,
    desconto_aplicado DECIMAL(10,2) DEFAULT 0,
    preco_original DECIMAL(10,2) NOT NULL,
    preco_final DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (venda_item_id) REFERENCES venda_itens(id) ON DELETE CASCADE,
    FOREIGN KEY (promocao_id) REFERENCES promocoes(id) ON DELETE SET NULL,
    INDEX idx_venda_item (venda_item_id),
    INDEX idx_promocao (promocao_id));
-- Extraindo dados da tabela `tipos_promocao`
--

INSERT INTO `tipos_promocao` (`id`, `codigo`, `nome`, `descricao`, `ativo`) VALUES
(1, 'DESC_PERC', 'Desconto Percentual', 'Desconto em percentagem sobre o valor', 1),
(2, 'DESC_FIXO', 'Desconto Valor Fixo', 'Desconto com valor fixo', 1),
(3, 'COMPRE_X_LEVE_Y', 'Compre X Leve Y', 'Promoção compre X leve Y grátis', 1),
(4, 'COMBO', 'Combo/Pacote', 'Pacote com múltiplos produtos', 1),
(5, 'DESC_PROGRESSIVO', 'Desconto Progressivo', 'Desconto aumenta com o valor da compra', 1),
(6, 'DESC_CLIENTE', 'Desconto Cliente', 'Desconto específico para cliente', 1),
(7, 'DESC_CATEGORIA', 'Desconto Categoria', 'Desconto para categoria inteira', 1);



CREATE TABLE devolucoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    numero_venda_id INT NOT NULL, -- ligação à venda original
    venda_nc_id INT NOT NULL,
	motivo_id INT NULL,
    sessao_id INT NOT NULL, -- controlo de caixa      -- caixa aberto
    pdv_id INT NOT NULL,
    usuario_id int NOT NULL,
	forma_pagamento_id int NOT NULL,
	tipo enum('parcial','total') NOT NULL,
	observacoes TEXT,
    cliente_id INT,
    numero_documento_fiscal varchar(50) UNIQUE DEFAULT NULL,
    tipo_documento_fiscal varchar(10) DEFAULT 'NC',
    hash_controlo varchar(100) DEFAULT NULL,
    data_emissao_fiscal datetime DEFAULT NULL,
    motivo_codigo varchar(20) DEFAULT NULL,
    base_incidencia decimal(10,2) DEFAULT NULL,
    valor_iva decimal(10,2) DEFAULT NULL,
    total_sem_iva decimal(10,2) DEFAULT NULL,
    hash_assinatura varchar(255) DEFAULT NULL,
    codigo_controlo varchar(50) DEFAULT NULL,
    qr_code text,
    numero_original_documento varchar(50) DEFAULT NULL,
    serie_original varchar(5) DEFAULT NULL,
    data_original date DEFAULT NULL,
    nif_cliente_original varchar(20) DEFAULT NULL,
	data_devolucao DATETIME DEFAULT CURRENT_TIMESTAMP,
    motivo VARCHAR(255),
    total_devolucao DECIMAL(18,2),
    estado enum('pendente','processada','cancelada', 'aprovada', 'rejeitada') DEFAULT 'processada',
	created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (numero_venda_id) REFERENCES vendas(id),
	FOREIGN KEY (forma_pagamento_id) REFERENCES formas_pagamento(id),
    FOREIGN KEY (venda_nc_id) REFERENCES vendas(id),
	FOREIGN KEY (motivo_id) REFERENCES motivos_devolucao_agt(id),
    FOREIGN KEY (sessao_id) REFERENCES caixa_sessao(id),
    FOREIGN KEY (pdv_id) REFERENCES pdv(id),
	FOREIGN KEY (cliente_id) REFERENCES clientes(id)),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id));

CREATE TABLE IF NOT EXISTS logs_auditoria_devolucoes (
  id INT PRIMARY KEY AUTO_INCREMENT,
  devolucao_id int NOT NULL,
  usuario_id int NOT NULL,
  acao varchar(100) NOT NULL,
  dados_antes text,
  dados_depois text,
  ip_address varchar(45) DEFAULT NULL,
  created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (devolucao_id) REFERENCES devolucoes(id) ON DELETE CASCADE,
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id));
  
CREATE TABLE IF NOT EXISTS motivos_devolucao_agt (
  id INT PRIMARY KEY AUTO_INCREMENT,
  codigo varchar(10) NOT NULL UNIQUE,
  descricao varchar(255) NOT NULL,
  ativo tinyint(1) DEFAULT '1');
INSERT INTO `motivos_devolucao_agt` (`id`, `codigo`, `descricao`, `ativo`) VALUES
(1, '01', 'Mercadoria com defeito', 1),
(2, '02', 'Mercadoria não conforme', 1),
(3, '03', 'Mercadoria avariada', 1),
(4, '04', 'Erro na quantidade', 1),
(5, '05', 'Erro no preço', 1),
(6, '06', 'Desistência do cliente', 1),
(7, '07', 'Prazo de garantia', 1),
(8, '08', 'Devolução por troca', 1),
(9, '09', 'Cancelamento de encomenda', 1),
(10, '10', 'Outros motivos', 1);



CREATE TABLE devolucao_itens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    devolucao_id INT NOT NULL,
    venda_itens_id INT NOT NULL,
    produto_id INT NOT NULL,
    quantidade_devolvida DECIMAL(18,3),
    valor_unitario DECIMAL(18,2),
    total_linha DECIMAL(18,2),
	iva_taxa DECIMAL(5,2) NOT NULL,
	base_incidencia decimal(10,2) DEFAULT NULL,
    valor_iva decimal(10,2) DEFAULT NULL,
    codigo_iva varchar(2) DEFAULT NULL,
    regime_iva varchar(20) DEFAULT NULL,
    motivo_isencao text,
	data_devolucao DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (devolucao_id) REFERENCES devolucoes(id),
    FOREIGN KEY (venda_itens_id) REFERENCES venda_itens(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id));

CREATE TABLE logs_sistema (
    id INT PRIMARY KEY AUTO_INCREMENT,
    loja_id INT,
    usuario_id INT,
    acao VARCHAR(100) NOT NULL,
    descricao TEXT,
	ip_address varchar(50) DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (loja_id) REFERENCES lojas(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id));

CREATE TABLE IF NOT EXISTS cartoes_cliente (
  id INT PRIMARY KEY AUTO_INCREMENT,
  numero_cartao varchar(20) UNIQUE,
  codigo_barras varchar(20) UNIQUE,
  cliente_id int DEFAULT NULL,
  senha_hash varchar(255) NOT NULL,
  saldo decimal(10,2) DEFAULT '0.00',
  saldo_bloqueado decimal(10,2) DEFAULT '0.00',
  limite_credito decimal(10,2) DEFAULT '0.00',
  data_validade date DEFAULT NULL,
  estado enum('ativo','bloqueado','expirado','cancelado') DEFAULT 'ativo',
  data_emissao date NOT NULL,
  data_ultima_utilizacao datetime DEFAULT NULL,
  total_compras decimal(10,2) DEFAULT '0.00',
  loja_id int NOT NULL,
  created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (loja_id) REFERENCES loja(id),
  FOREIGN KEY (cliente_id) REFERENCES clientes(id));
INSERT INTO `cartoes_cliente` (`id`, `numero_cartao`, `codigo_barras`, `cliente_id`, `senha_hash`, `saldo`, `saldo_bloqueado`, `limite_credito`, `data_validade`, `estado`, `data_emissao`, `data_ultima_utilizacao`, `total_compras`, `loja_id`, `created_at`, `updated_at`) VALUES
(1, '1000165425112873', '1000165425112873', 1, '123456', 10209.23, 0.00, 0.00, '2027-11-28', 'ativo', '2025-11-28', '2026-01-23 23:19:45', 0.00, 1, '2025-11-28 20:36:00', '2026-01-23 22:19:45'),
(2, '1000165425112874', '1000165425112874', NULL, '654321', 75.50, 0.00, 0.00, '2027-11-28', 'ativo', '2025-11-28', NULL, 0.00, 1, '2025-11-28 20:36:00', '2025-11-28 20:36:00'),
(3, '1000176511009995', '1000176511009995', 3, '1234', 93384.00, 0.00, 1000000.00, '2027-12-07', 'ativo', '2025-12-07', '2025-12-07 13:37:09', 0.00, 1, '2025-12-07 11:22:14', '2025-12-07 11:37:09');
  
CREATE TABLE carregamentos_cartao (
  id INT PRIMARY KEY AUTO_INCREMENT,
  cartao_id int NOT NULL,
  valor decimal(10,2) NOT NULL,
  forma_pagamento_id int NOT NULL,
  referencia varchar(100) DEFAULT NULL,
  observacoes text,
  usuario_id int NOT NULL,
  pdv_id int NOT NULL,
  loja_id INT NOT NULL,
  created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (loja_id) REFERENCES loja(id),
  FOREIGN KEY (forma_pagamento_id) REFERENCES formas_pagamento(id),
  FOREIGN KEY (pdv_id) REFERENCES pdv(id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  FOREIGN KEY (cartao_id) REFERENCES cartoes_cliente(id)  );
INSERT INTO `carregamentos_cartao` (`id`, `cartao_id`, `valor`, `forma_pagamento_id`, `referencia`, `observacoes`, `usuario_id`, `caixa_id`, `loja_id`, `created_at`) VALUES
(1, 1, 20000.00, 1, '2135', NULL, 1, 1, 1, '2025-12-01 22:11:50');


CREATE TABLE IF NOT EXISTS movimentos_cartao (
  id int PRIMARY KEY AUTO_INCREMENT,
  cartao_id int NOT NULL,
  tipo enum('carregamento','pagamento','estorno','consulta','bloqueio','desbloqueio') DEFAULT NULL,
  valor decimal(10,2) DEFAULT '0.00',
  saldo_anterior decimal(10,2) DEFAULT '0.00',
  saldo_posterior decimal(10,2) DEFAULT '0.00',
  descricao text,
  referencia varchar(100) DEFAULT NULL,
  usuario_id int DEFAULT NULL,
  pdv_id int DEFAULT NULL,
  loja_id int NOT NULL,
  created_at timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (loja_id) REFERENCES lojas(id),
  FOREIGN KEY (pdv_id) REFERENCES pdv(id),
  FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
  FOREIGN KEY (cartao_id) REFERENCES cartoes_cliente(id));

CREATE TABLE IF NOT EXISTS descontos_manuais (
    id INT PRIMARY KEY AUTO_INCREMENT,
    venda_id INT NOT NULL,
    tipo VARCHAR(20) DEFAULT 'manual',
    valor DECIMAL(10,2) NOT NULL,
    percentual VARCHAR(10) NULL,
    aplicado_por VARCHAR(100) NOT NULL,
    supervisor VARCHAR(100) NULL,
    data_aplicacao DATETIME NOT NULL,
	usuario_id int DEFAULT NULL,
	supervisor_id INT NULL,
	supervisor_nome VARCHAR(100) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
	FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
	FOREIGN KEY (supervisor_id) REFERENCES usuarios(id) ON DELETE SET NULL,
    FOREIGN KEY (venda_id) REFERENCES vendas(id) ON DELETE CASCADE);

CREATE TABLE IF NOT EXISTS motivos_isencao_iva (
    id INT PRIMARY KEY AUTO_INCREMENT,
    codigo VARCHAR(10) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL,
    ativo BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir motivos de isenção conforme legislação angolana
INSERT INTO motivos_isencao_iva (codigo, descricao) VALUES
('M01', 'Exportação de bens'),
('M02', 'Transporte internacional de mercadorias'),
('M03', 'Transmissão de bens para organizações internacionais'),
('M04', 'Operações relacionadas com ouro'),
('M05', 'Fornecimento de bens a navios e aeronaves'),
('M06', 'Operações financeiras e de seguros'),
('M07', 'Prestações de serviços médicos e hospitalares'),
('M08', 'Ensino e formação profissional'),
('M09', 'Serviços culturais e desportivos'),
('M10', 'Operações imobiliárias'),
('M11', 'Isenção por força de contratos internacionais'),
('M12', 'Outras isenções previstas no CIVA')
ON DUPLICATE KEY UPDATE descricao = VALUES(descricao);

-- 1.2. Criar tabela de regimes especiais de IVA
CREATE TABLE IF NOT EXISTS regimes_especiais_iva (
    id INT PRIMARY KEY AUTO_INCREMENT,
    codigo VARCHAR(10) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL,
    ativo BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO regimes_especiais_iva (codigo, descricao) VALUES
('R01', 'Regime de tributação de margem - bens em segunda mão'),
('R02', 'Regime de tributação de margem - objetos de arte'),
('R03', 'Regime de tributação de margem - coleções e antiguidades'),
('R04', 'Regime especial das agências de viagens'),
('R05', 'Regime especial dos pequenos retalhistas'),
('R06', 'Regime especial da agricultura, pecuária e pescas')
ON DUPLICATE KEY UPDATE descricao = VALUES(descricao);

CREATE TABLE IF NOT EXISTS codigos_erro_agt (
    id INT PRIMARY KEY AUTO_INCREMENT,
    codigo VARCHAR(20) NOT NULL UNIQUE,
    descricao VARCHAR(255) NOT NULL,
    tipo ENUM('erro', 'aviso', 'rejeicao') DEFAULT 'erro',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO codigos_erro_agt (codigo, descricao, tipo) VALUES
('AGT001', 'NIF do emitente inválido', 'erro'),
('AGT002', 'NIF do adquirente inválido', 'erro'),
('AGT003', 'Série de documento inválida', 'erro'),
('AGT004', 'Número de documento já existe', 'rejeicao'),
('AGT005', 'Hash de validação incorreto', 'rejeicao'),
('AGT006', 'Data de emissão inválida', 'erro'),
('AGT007', 'Total do documento não coincide', 'erro'),
('AGT008', 'Valor de IVA não coincide', 'erro'),
('AGT009', 'Produto sem código de IVA válido', 'aviso'),
('AGT010', 'Motivo de isenção não especificado', 'aviso')
ON DUPLICATE KEY UPDATE descricao = VALUES(descricao);





INSERT INTO `clientes` (`id`, `loja_id`, `nif`, `nome`, `endereco`, `telefone`, `email`, `tipo_cliente`, `ativo`, `created_at`) VALUES
(1, 1, '123876534', 'Paulo Antonio', 'Luanda', '+244 222 333 444', 'paulo@gmail.com', 'Sujeito Passivo', 1, '2025-12-18 22:19:15'),
(2, 1, '762899LD8', 'Mateus Santos', 'luanda', '74098836', 'mateus@gmail.com', 'Consumidor Final', 1, '2025-12-18 22:19:15');

INSERT INTO `empresa` (`id`, `nif`, `nome`, `nome_comercial`, `endereco`, `cidade`, `pais`, `atividade_principal`, `codigo_postal`, `municipio`, `provincia`, `telefone`, `email`, `created_at`) VALUES
(1, '999999999', 'Sua Empresa', 'Sua Empresa', 'Luanda Maianga', 'Luandac', 'Angola', NULL, NULL, 'Luanda', 'Luanda', '+244 222 333 444', 'contato@nosaempre.ao', '2025-12-15 21:33:36'),
(2, '500000000LA001', 'TECNOLOGIA ANGOLA LDA', 'TECNOLOGIA ANGOLA LDA', 'Luanda Viana', 'Luanda', 'Angola', 'Comercio geral', NULL, 'Viana', 'Luanda', '+244 222 333 427', 'contato@techstore.ao', '2025-12-15 21:33:36');



INSERT INTO `loja` (`id`, `empresa_id`, `codigo`, `nome`, `endereco`, `ativo`) VALUES
(1, 1, '0001', 'loja Maianga', 'Maianga', 1),
(2, 1, '0002', 'Loja viana', 'Viana', 1);

INSERT INTO `pdv` (`id`, `loja_id`, `codigo`, `numero`, `descricao`, `ativo`) VALUES
(1, 1, '001', 1, 'frente loja1 ', 1),
(2, 1, '002', 2, 'frente loja 2', 1),
(3, 2, '003', 3, 'POS3', 1);

INSERT INTO `produtos` (`id`, `loja_id`, `categoria_id`, `codigo`, `descricao`, `tipo`, `unidade_medida`, `preco_venda`, `preco_custo`, `taxa_id`, `stock_minimo`, `stock_atual`, `stock_reservado`, `localizacao_armazem`, `created_at`, `updated_at`, `ativo`) VALUES
(1, 1, 1, '5601000000123', 'Arroz Agulha (1kg)', 'PESO', 'KG', 200.00, 100.00, 2, 50.000, 149.000, -1.000, 'Corredor A, Prateleira 1', '2025-12-15 18:58:19', '2025-12-18 20:19:52', 1),
(2, 1, 1, '5601000000234', 'Azeite Virgem (750ml)', 'UNIDADE', 'UN', 6.99, 4.50, 1, 30.000, 80.000, 0.000, 'Corredor A, Prateleira 2', '2025-12-15 18:58:19', '2025-12-15 18:58:19', 1),
(3, 1, 2, '4897057900065', 'Água Mineral (1.5L)', 'UNIDADE', 'UN', 8000.00, 7000.00, 1, 100.000, 125.000, -175.000, 'Corredor B, Prateleira 1', '2025-12-15 18:58:19', '2026-02-04 22:03:14', 1),
(4, 1, 2, '5407010261431', 'Refrigerante Cola (330ml)', 'UNIDADE', 'UN', 5000.00, 4000.00, 4, 50.000, 100.000, -120.000, 'Corredor B, Prateleira 2', '2025-12-15 18:58:19', '2026-01-06 22:48:57', 1),
(5, 1, 3, '5603000000567', 'Detergente Loiça (1L)', 'UNIDADE', 'UN', 2.30, 1.10, 1, 40.000, 95.000, 0.000, 'Corredor C, Prateleira 1', '2025-12-15 18:58:19', '2025-12-15 18:58:19', 1),
(6, 1, 4, '5604000000678', 'Pasta de Dentes (100g)', 'UNIDADE', 'UN', 2000.00, 1500.00, 1, 60.000, 180.000, 0.000, 'Corredor D, Prateleira 1', '2025-12-15 18:58:19', '2025-12-18 20:16:28', 1),
(7, 1, 5, '5605000000789', 'Pão Alentejano', 'PESO', 'KG', 3.50, 1.50, 1, 10.000, 45.000, 0.000, 'Secção Padaria', '2025-12-15 18:58:19', '2025-12-15 18:58:19', 1),
(8, 1, 5, '5449000000996', 'Bolo de Arroz (Unid.)', 'UNIDADE', 'UN', 500.00, 300.00, 3, 20.000, 0.000, -60.000, 'Secção Padaria', '2025-12-15 18:58:19', '2025-12-26 16:07:54', 1),
(9, 1, 6, '5606000000901', 'Bife de Vaca (Corte)', 'PESO', 'KG', 12.50, 8.00, 1, 5.000, 20.000, 0.000, 'Câmara Frigorífica', '2025-12-15 18:58:19', '2025-12-15 18:58:19', 1),
(10, 1, 6, '5606000001012', 'Frango Inteiro (Cong.)', 'PESO', 'KG', 4.90, 2.50, 1, 15.000, 50.000, 0.000, 'Câmara Frigorífica', '2025-12-15 18:58:19', '2025-12-15 18:58:19', 1);

INSERT INTO `sequencias_vendas` (`id`, `loja_id`, `pdv_id`, `tipo_venda`, `ano`, `ultimo_numero`, `data_ultima_emissao`) VALUES
(1, 1, 1, 'FT', 2025, 10, '2025-12-26 18:07:54'),
(2, 1, 1, 'FR', 2025, 28, '2025-12-26 17:57:12'),
(3, 1, 1, 'FS', 2025, 66, '2025-12-23 23:21:24'),
(4, 1, 1, 'NC', 2025, 0, NULL),
(5, 1, 1, 'ND', 2025, 0, NULL),
(6, 1, 1, 'FS', 2026, 16, '2026-02-04 23:01:54'),
(7, 1, 1, 'FR', 2026, 4, '2026-02-04 23:03:14'),
(8, 1, 1, 'FT', 2026, 10, '2026-01-06 23:48:57');



INSERT INTO `tipos_documento` (`id`, `codigo`, `nome`, `descricao`) VALUES
(1, 'FT', 'Factura', NULL),
(2, 'FR', 'Factura-Recibo', NULL),
(3, 'FS', 'Factura Simplificada', NULL),
(4, 'NC', 'Nota de Crédito', NULL),
(5, 'ND', 'Nota de Débito', NULL),
(6, 'CO', 'cont', NULL);

INSERT INTO `usuarios` (`id`, `loja_id`, `numero_trabalhador`, `nome`, `username`, `senha`, `perfil`, `per_venda`, `ativo`) VALUES
(1, 1, 1000, 'Mateus António', 'mateus.antonio', '12345', 'admin', '1', 1),
(2, 1, 2064, 'Ana Bela', 'ana.bela', '12345', 'operador', '1', 1),
(3, 1, 3002, 'Paulo Martins', 'paulo.martins', '12345', 'supervisor', '1', 1),
(4, 1, 2065, 'Bela Ana', 'bela.ana', '12345', 'operador', '1', 1);





