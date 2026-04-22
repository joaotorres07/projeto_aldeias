CREATE DATABASE `db_aldeias`;
use db_aldeias;

CREATE TABLE `tb_nucleo` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `tb_aldeeiro` (
  `nome` varchar(50) NOT NULL,
  `cpf` varchar(20) NOT NULL,
  `data_nascimento` date NOT NULL,
  `telefone` varchar(25) NOT NULL,
  `email` varchar(30) NOT NULL,
  `nucleo` int NOT NULL,
  `ja_serviu` tinyint(1) NOT NULL DEFAULT '0',
  `data_insert` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `data_update` timestamp NULL DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`cpf`),
  KEY `fk_tb_aldeeiro_nucleo` (`nucleo`),
  CONSTRAINT `fk_tb_aldeeiro_nucleo` FOREIGN KEY (`nucleo`) REFERENCES `tb_nucleo` (`id`)
);

CREATE TABLE `tb_aldeia` (
  `id` decimal(10,0) NOT NULL,
  `nome_aldeia` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `tb_aldeeiro_aldeia_fez` (
  `cpf_aldeeiro` varchar(20) NOT NULL,
  `id_aldeia` decimal(10,0) NOT NULL,
  PRIMARY KEY (`cpf_aldeeiro`,`id_aldeia`),
  KEY `fk_aa_aldeia` (`id_aldeia`),
  CONSTRAINT `fk_aaf_aldeeiro` FOREIGN KEY (`cpf_aldeeiro`) REFERENCES `tb_aldeeiro` (`cpf`) ON DELETE CASCADE,
  CONSTRAINT `fk_aaf_aldeia` FOREIGN KEY (`id_aldeia`) REFERENCES `tb_aldeia` (`id`) ON DELETE CASCADE
);

CREATE TABLE `tb_aldeeiro_aldeia_serviu` (
  `cpf_aldeeiro` varchar(20) NOT NULL,
  `id_aldeia` decimal(10,0) NOT NULL,
  PRIMARY KEY (`cpf_aldeeiro`,`id_aldeia`),
  KEY `fk_aa_aldeia` (`id_aldeia`),
  CONSTRAINT `fk_aa_aldeeiro` FOREIGN KEY (`cpf_aldeeiro`) REFERENCES `tb_aldeeiro` (`cpf`) ON DELETE CASCADE,
  CONSTRAINT `fk_aa_aldeia` FOREIGN KEY (`id_aldeia`) REFERENCES `tb_aldeia` (`id`) ON DELETE CASCADE
);

CREATE TABLE `tb_equipes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(50) NOT NULL,
  `funcao` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`)
);

CREATE TABLE `tb_aldeeiro_equipe` (
  `cpf_aldeeiro` varchar(20) NOT NULL,
  `id_equipe` int NOT NULL,
  PRIMARY KEY (`cpf_aldeeiro`,`id_equipe`),
  KEY `fk_ae_equipe` (`id_equipe`),
  CONSTRAINT `fk_ae_aldeeiro` FOREIGN KEY (`cpf_aldeeiro`) REFERENCES `tb_aldeeiro` (`cpf`) ON DELETE CASCADE,
  CONSTRAINT `fk_ae_equipe` FOREIGN KEY (`id_equipe`) REFERENCES `tb_equipes` (`id`) ON DELETE CASCADE
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
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_formacao_nucleo_data` (`tema`,`nucleo`,`data_formacao`),
  KEY `fk_tb_formacao_nucleo` (`nucleo`),
  CONSTRAINT `fk_tb_formacao_nucleo` FOREIGN KEY (`nucleo`) REFERENCES `tb_nucleo` (`id`)
);

CREATE TABLE `tb_frequencia_aldeeiro` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id_formacao` int NOT NULL,
  `cpf_aldeeiro` varchar(20) NOT NULL,
  `presente` tinyint(1) NOT NULL DEFAULT '0',
  `data_registro` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_freq_formacao_aldeeiro` (`id_formacao`,`cpf_aldeeiro`),
  KEY `fk_freq_aldeeiro` (`cpf_aldeeiro`),
  CONSTRAINT `fk_freq_aldeeiro` FOREIGN KEY (`cpf_aldeeiro`) REFERENCES `tb_aldeeiro` (`cpf`) ON DELETE CASCADE,
  CONSTRAINT `fk_freq_formacao` FOREIGN KEY (`id_formacao`) REFERENCES `tb_formacao` (`id`) ON DELETE CASCADE
);

-- INSERTS INICIAIS

INSERT INTO `tb_nucleo` VALUES (1,'Belo Horizonte'),(2,'Campo Belo'),(3,'Lavras'),(4,'Alfenas'),(5,'Perdões');
INSERT INTO `tb_perfil` VALUES (1,'Aldeeiro'),(2,'Formador'),(3,'Coordenador'), (4, 'Administrador');
INSERT INTO `tb_aldeia` VALUES (1,'Aldeia de Aprofundamento'),(2,'Aldeia de Adolescentes'),(3,'Aldeia de Recomeço'),(4,'Aldeia de Aliança de Vida'),(5,'Aldeia de Crescimento'),(6,'Aldeia em Familia'),(7,'Aldeia de Jovens'),(8,'Aldeia da Melhor Idade'),(9,'Aldeia de Compromisso');
INSERT INTO `tb_equipes` VALUES (1,'Banda','Musica e som'),(2,'Cozinha','Alimentação'),(3,'Liderança','Cuidar do aldeeiro'),(4,'Serviços Gerais','Montagem dos desafios e suporte na solução em eventuais problemas'),(5,'Pequenos Gestos','Organizar locais e encenações'),(6,'Apoio','Responsável pela limpeza do local da aldeia'),(7,'Mediadores','Conduzir a tribo e fazer as reflexões espirituais de cada desafio'),(8,'Virgilia','Orações antes e durante a aldeia'),(9,'Visitação','Pegar as cartas e conduzir a familia do aldeeiro para o momento final'),(10,'Guardião','Fiscalizar a aldeia para o Pe. Pedro'),(11,'Dirigente','Dirigir e conduzir toda a aldeia'),(12,'Segurança','Monitorar as entradas do local para que não ocorra acessos e saídas indevidas'),(13,'Conselheiros','Organizar a aldeia antes e durante e após fazer todos os relatórios'),(14,'Externa','Sair da aldeia para comprar/buscar materiais ou qualquer serviço necessário');

ALTER TABLE db_aldeias.tb_aldeeiro
ADD COLUMN sexo CHAR(1) NOT NULL
CHECK (sexo IN ('F', 'M'))
AFTER `data_nascimento`;


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

ALTER TABLE `tb_aldeeiro`
ADD COLUMN `logradouro` VARCHAR(100) NULL AFTER `ativo`,
ADD COLUMN `numero` VARCHAR(10) NULL AFTER `logradouro`,
ADD COLUMN `complemento` VARCHAR(50) NULL AFTER `numero`,
ADD COLUMN `bairro` VARCHAR(50) NULL AFTER `complemento`,
ADD COLUMN `cidade` VARCHAR(50) NULL AFTER `bairro`,
ADD COLUMN `uf` CHAR(2) NULL AFTER `cidade`;
