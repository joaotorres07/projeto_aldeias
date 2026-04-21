USE db_aldeias;

-- Adicionar perfil Administrador
INSERT INTO `tb_perfil` VALUES (4, 'Administrador');

-- Para vincular o perfil de Administrador a um aldeeiro existente, execute:
-- Substitua 'SEU_CPF_AQUI' pelo CPF do aldeeiro que será administrador
-- INSERT INTO `tb_aldeeiro_perfil` (cpf_aldeeiro, id_perfil) VALUES ('SEU_CPF_AQUI', 4);

-- Ou vincule pelo email do usuário:
-- INSERT INTO `tb_aldeeiro_perfil` (cpf_aldeeiro, id_perfil)
-- SELECT a.cpf, 4 FROM `tb_aldeeiro` a WHERE a.email = 'SEU_EMAIL_AQUI';

-- Tabela de usuário do sistema (login)
CREATE TABLE IF NOT EXISTS `tb_usuario` (
  `id` int NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `senha_hash` varchar(256) NOT NULL,
  `data_criacao` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `ativo` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_usuario_email` (`email`)
);

