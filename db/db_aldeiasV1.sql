CREATE DATABASE `db_aldeias`;
use db_aldeias;

CREATE TABLE `tb_nucleo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) NOT NULL,
  `endereco` varchar(200) NOT NULL,
  `dias_reuniao` varchar(100) NOT NULL,
  `ativo_relatorio` tinyint(1) NOT NULL DEFAULT '1',
  `motivo_alteracao` varchar(200) NOT NULL,
  `data_criacao` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_update` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `cpf_alterou` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `tb_aldeeiro` (
  `nome` varchar(50) NOT NULL,
  `cpf` varchar(20) NOT NULL,
  `data_nascimento` date NOT NULL,
  `sexo` char(1) NOT NULL CHECK (`sexo` IN ('F', 'M')),
  `telefone` varchar(25) NOT NULL,
  `email` varchar(30) NOT NULL,
  `nucleo` int NOT NULL,
  `ja_serviu` tinyint(1) NOT NULL DEFAULT '0',
  `data_insert` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_update` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  `logradouro` varchar(100) NULL,
  `numero` varchar(10) NULL,
  `complemento` varchar(50) NULL,
  `bairro` varchar(50) NULL,
  `cidade` varchar(50) NULL,
  `uf` char(2) NULL,
  PRIMARY KEY (`cpf`),
  KEY `fk_tb_aldeeiro_nucleo` (`nucleo`),
  CONSTRAINT `fk_tb_aldeeiro_nucleo` FOREIGN KEY (`nucleo`) REFERENCES `tb_nucleo` (`id`)
);

CREATE TABLE `tb_aldeia` (
  `id` decimal(10,0) NOT NULL,
  `nome_aldeia` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `tb_equipes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) NOT NULL,
  `funcao` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `tb_aldeeiro_aldeia_fez` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cpf_aldeeiro` varchar(20) NOT NULL,
  `id_aldeia` decimal(10,0) NOT NULL,
  `data_aldeia` date NULL,
  `id_nucleo` int NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_aldeeiro_aldeia_fez` (`cpf_aldeeiro`, `id_aldeia`),
  KEY `fk_aaf_aldeia` (`id_aldeia`),
  KEY `fk_aaf_nucleo` (`id_nucleo`),
  CONSTRAINT `fk_aaf_aldeeiro` FOREIGN KEY (`cpf_aldeeiro`) REFERENCES `tb_aldeeiro` (`cpf`) ON DELETE CASCADE,
  CONSTRAINT `fk_aaf_aldeia` FOREIGN KEY (`id_aldeia`) REFERENCES `tb_aldeia` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_aaf_nucleo` FOREIGN KEY (`id_nucleo`) REFERENCES `tb_nucleo` (`id`)
);

CREATE TABLE `tb_aldeeiro_aldeia_serviu` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cpf_aldeeiro` varchar(20) NOT NULL,
  `id_aldeia` decimal(10,0) NOT NULL,
  `data_aldeia` date NULL,
  `id_equipe` int NULL,
  `id_nucleo` int NULL,
  PRIMARY KEY (`id`),
  KEY `fk_aas_aldeia` (`id_aldeia`),
  KEY `fk_aas_equipe` (`id_equipe`),
  KEY `fk_aas_nucleo` (`id_nucleo`),
  CONSTRAINT `fk_aas_aldeeiro` FOREIGN KEY (`cpf_aldeeiro`) REFERENCES `tb_aldeeiro` (`cpf`) ON DELETE CASCADE,
  CONSTRAINT `fk_aas_aldeia` FOREIGN KEY (`id_aldeia`) REFERENCES `tb_aldeia` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_aas_equipe` FOREIGN KEY (`id_equipe`) REFERENCES `tb_equipes` (`id`),
  CONSTRAINT `fk_aas_nucleo` FOREIGN KEY (`id_nucleo`) REFERENCES `tb_nucleo` (`id`)
);

CREATE TABLE `tb_perfil` (
  `id` int NOT NULL,
  `descricao` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `chk_tb_perfil_id` CHECK ((`id` between 1 and 10))
);

CREATE TABLE `tb_aldeeiro_perfil` (
  `cpf_aldeeiro` varchar(20) NOT NULL,
  `id_perfil` int NOT NULL,
  PRIMARY KEY (`cpf_aldeeiro`,`id_perfil`),
  KEY `fk_ap_perfil` (`id_perfil`),
  CONSTRAINT `fk_ap_aldeeiro` FOREIGN KEY (`cpf_aldeeiro`) REFERENCES `tb_aldeeiro` (`cpf`) ON DELETE CASCADE,
  CONSTRAINT `fk_ap_perfil` FOREIGN KEY (`id_perfil`) REFERENCES `tb_perfil` (`id`) ON DELETE RESTRICT
);

CREATE TABLE `tb_formacao` (
  `id` int NOT NULL AUTO_INCREMENT,
  `tema` varchar(50) NOT NULL,
  `data_formacao` date DEFAULT NULL,
  `nucleo` int NOT NULL,
  `cpf_formador` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_formacao_nucleo_data` (`tema`,`nucleo`,`data_formacao`),
  KEY `fk_tb_formacao_nucleo` (`nucleo`),
  KEY `fk_formacao_formador` (`cpf_formador`),
  CONSTRAINT `fk_tb_formacao_nucleo` FOREIGN KEY (`nucleo`) REFERENCES `tb_nucleo` (`id`),
  CONSTRAINT `fk_formacao_formador` FOREIGN KEY (`cpf_formador`) REFERENCES `tb_aldeeiro` (`cpf`)
);

CREATE TABLE `tb_frequencia_aldeeiro` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_formacao` int NOT NULL,
  `cpf_aldeeiro` varchar(20) NOT NULL,
  `data_registro` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_freq_formacao_aldeeiro` (`id_formacao`,`cpf_aldeeiro`),
  KEY `fk_freq_aldeeiro` (`cpf_aldeeiro`),
  CONSTRAINT `fk_freq_aldeeiro` FOREIGN KEY (`cpf_aldeeiro`) REFERENCES `tb_aldeeiro` (`cpf`) ON DELETE CASCADE,
  CONSTRAINT `fk_freq_formacao` FOREIGN KEY (`id_formacao`) REFERENCES `tb_formacao` (`id`) ON DELETE CASCADE
);

CREATE TABLE `tb_usuario` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `senha_hash` varchar(256) NOT NULL,
  `data_criacao` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_usuario_email` (`email`)
);

CREATE TABLE `tb_recuperacao_senha` (
  `id` int NOT NULL AUTO_INCREMENT,
  `usuario_id` int NOT NULL,
  `codigo` varchar(6) NOT NULL,
  `criado_em` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `usado` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `fk_recup_usuario` (`usuario_id`),
  CONSTRAINT `fk_recup_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `tb_usuario` (`id`) ON DELETE CASCADE
);

-- Dados iniciais
INSERT INTO `tb_nucleo` (`id`,`nome`,`endereco`,`dias_reuniao`,`ativo_relatorio`,`motivo_alteracao`,`data_criacao`,`data_update`,`cpf_alterou`)
VALUES (1,'Belo Horizonte','Rua Sergipe 175, esquina com Rua dos Timbiras - Centro, BH. Entrada pela rua de trás da paróquia.','Segunda-Feira 19:30',1,'Criação inicial',CURRENT_TIMESTAMP,NULL,'system_default'),
(2,'Campo Belo','','',1,'Criação inicial',CURRENT_TIMESTAMP,NULL,'system_default'),
(3,'Lavras','','',1,'Criação inicial',CURRENT_TIMESTAMP,NULL,'system_default'),
(4,'Alfenas','','',0,'Criação inicial',CURRENT_TIMESTAMP,NULL,'system_default'),
(5,'Perdões','','',1,'Criação inicial',CURRENT_TIMESTAMP,NULL,'system_default'),
(6, 'Paraguaçu', '', '', 0, 'Criação inicial', CURRENT_TIMESTAMP, 'system_default', 'system_default'),
(7, 'Alpinopolis', '', '', 0, 'Criação inicial', CURRENT_TIMESTAMP, NULL, 'system_default'),
(8, 'Lorena', '', '', 0, 'Criação inicial', CURRENT_TIMESTAMP, NULL, 'system_default'),
(9, 'Taubaté', '', '', 0, 'Criação inicial', CURRENT_TIMESTAMP, NULL, 'system_default'),
(10, 'Três Corações', '', '', 0, 'Criação inicial', CURRENT_TIMESTAMP, NULL, 'system_default');
INSERT INTO `tb_perfil` VALUES (1,'Aldeeiro'),(2,'Formador'),(3,'Coordenador'), (4, 'Administrador'), (5, 'Fundador'), (6, 'Usuário');
INSERT INTO `tb_aldeia` VALUES (1,'Aldeia de Aprofundamento'),(2,'Aldeia de Adolescentes'),(3,'Aldeia de Recomeço'),(4,'Aldeia de Aliança de Vida'),(5,'Aldeia de Crescimento'),(6,'Aldeia em Familia'),(7,'Aldeia de Jovens'),(8,'Aldeia da Melhor Idade'),(9,'Aldeia de Compromisso');
INSERT INTO `tb_equipes` VALUES (1,'Banda','Musica e som'),(2,'Cozinha','Alimentação'),(3,'Liderança','Cuidar do aldeeiro'),(4,'Serviços Gerais','Montagem dos desafios e suporte na solução em eventuais problemas'),(5,'Pequenos Gestos','Organizar locais e encenações'),(6,'Apoio','Responsável pela limpeza do local da aldeia'),(7,'Mediadores','Conduzir a tribo e fazer as reflexões espirituais de cada desafio'),(8,'Virgilia','Orações antes e durante a aldeia'),(9,'Visitação','Pegar as cartas e conduzir a familia do aldeeiro para o momento final'),(10,'Guardião','Fiscalizar a aldeia para o Pe. Pedro'),(11,'Dirigente','Dirigir e conduzir toda a aldeia'),(12,'Segurança','Monitorar as entradas do local para que não ocorra acessos e saídas indevidas'),(13,'Conselheiros','Organizar a aldeia antes e durante e após fazer todos os relatórios'),(14,'Externa','Sair da aldeia para comprar/buscar materiais ou qualquer serviço necessário');

-- Índices
CREATE INDEX idx_aldeeiro_nome ON tb_aldeeiro (nome);
CREATE INDEX idx_aldeeiro_cidade_uf ON tb_aldeeiro (cidade, uf);
CREATE INDEX idx_freq_formacao ON tb_frequencia_aldeeiro (id_formacao);
CREATE INDEX idx_freq_aldeeiro ON tb_frequencia_aldeeiro (cpf_aldeeiro);
CREATE INDEX idx_formacao_nucleo ON tb_formacao (nucleo);
CREATE INDEX idx_formacao_data ON tb_formacao (data_formacao);
CREATE INDEX idx_aaf_aldeia ON tb_aldeeiro_aldeia_fez (id_aldeia);
CREATE INDEX idx_aaf_cpf ON tb_aldeeiro_aldeia_fez (cpf_aldeeiro);
CREATE INDEX idx_aas_aldeia ON tb_aldeeiro_aldeia_serviu (id_aldeia);
CREATE INDEX idx_aas_cpf ON tb_aldeeiro_aldeia_serviu (cpf_aldeeiro);
CREATE INDEX idx_aas_equipe ON tb_aldeeiro_aldeia_serviu (id_equipe);
CREATE INDEX idx_ap_perfil ON tb_aldeeiro_perfil (id_perfil);
CREATE INDEX idx_recup_usuario ON tb_recuperacao_senha (usuario_id);