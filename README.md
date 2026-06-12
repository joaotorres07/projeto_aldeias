# Sistema Aldeias de Vida

## Geral
O sistema Aldeias de Vida é uma plataforma que ajuda no suporte e organização da comunidade católica Aldeias de Vida. O software é desenvolvido utilizando a linguagem de programação Python, com o framework Django para o backend e React para o frontend. O sistema é projetado para ser intuitivo e fácil de usar, permitindo ao aldeeiros registrarem suas participações nos eventos do movimento, bem como para os organizadores gerenciarem as atividades e os dados dos participantes.

## Funcionalidades
- **Registro de Participação**: Os aldeeiros podem registrar suas participações nos eventos do movimento, incluindo informações como data, local e tipo de evento.
- **Gerenciamento de Eventos**: Os organizadores podem criar, editar e excluir eventos, além de visualizar a lista de participantes e suas informações.
- **Relatórios**: O sistema gera relatórios detalhados sobre a participação dos aldeeiros, permitindo aos organizadores analisar a participação e o engajamento da comunidade.
- **Autenticação e Autorização**: O sistema possui um sistema de autenticação robusto, garantindo que apenas usuários autorizados possam acessar determinadas funcionalidades.
- **Interface Responsiva**: O frontend é desenvolvido com React, garantindo uma experiência de usuário fluida e responsiva em diferentes dispositivos.
- **Integração com Redes Sociais**: O sistema permite a integração com redes sociais para facilitar o compartilhamento de eventos e atividades do movimento.

## Tecnologias Utilizadas
- **Backend**: Python, Django
- **Frontend**: React, JavaScript
- **Banco de Dados**: MySql
- **Controle de Versão**: Git, GitHub
- **Hospedagem**: AWS
- **Serviços AWS**: 
  - EC2 - Máquina que hospeda a aplicação python.
  - S3Bucket - Armazena os arquivos e informativos do sistema.
  - RDS - Servidor de banco de dados que hospeda a base MySql.
  - SES - Serviço de envio de e-mails para notificações e comunicações com os usuários.

## Enviroment Localhost
- **Observações:** 
  - O sistema por padrão gera usuarios com o perfil de aldeeiros, para criar um usuário com perfil de organizador, é necessário acessar o banco de dados e adicionar outros perfis ao usuário para acessar outras funções.
  - O sistema é configurado para rodar localmente utilizando o MySql como banco de dados, e as variáveis de ambiente são definidas para facilitar a configuração do ambiente de desenvolvimento.
  - A variável `TEMPLATES_DIR` é utilizada para definir o diretório onde os templates do sistema estão localizados, portanto adicione o seu diretório local como valor.
  - As credenciais de acesso ao banco e serviços AWS reais devem ser solicitadas a coordenação do movimento, caso seja necessário algum teste real no ambiente local.

### Variáveis de ambiente para configuração local do sistema Aldeias de Vida
```
AWS_ACCESS_KEY_ID=;AWS_REGION=;DB_HOST=localhost;DB_NAME=db_aldeias;DB_PASSWORD=root;DB_USER=root;S3_BUCKET_NAME=;AWS_SECRET_ACCESS_KEY=;TEMPLATES_DIR=/default/
```
