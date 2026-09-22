# Documentação Técnica — Sistema Aldeias de Vida

> Documento gerado a partir da análise do código-fonte (`application/`, `templates/`, `db/db_aldeiasV1.sql`).

---

## 1. Visão Geral

O **Sistema Aldeias de Vida** é uma aplicação web monolítica escrita em **Python + Flask**, com renderização server-side via **Jinja2**, persistência em **MySQL** e integrações com **AWS S3**, **AWS SES** e **WhatsApp Cloud API (Meta)**.

A aplicação apoia a gestão da comunidade: cadastro de membros (*aldeeiros*), controle de **núcleos**, abertura de **formações** e registro de **presença**, histórico de participação em **aldeias** (eventos) como participante ou servidor de **equipe**, geração de fichas de **entrevista** em PDF, distribuição de **arquivos informativos** e **comunicação em massa** por WhatsApp.

> ⚠️ **Nota:** o `README.md` do repositório menciona Django + React. O código real utiliza **Flask + Jinja2** (sem SPA React). Esta documentação reflete o código.

### Stack

| Camada | Tecnologia |
|---|---|
| Web framework | Flask (`app_flask.py`) |
| Templates | Jinja2 + Bootstrap (`templates/`) |
| Banco | MySQL via `pymysql` + `DBUtils.PooledDB` |
| Hash de senha | `werkzeug.security` (`generate_password_hash` / `check_password_hash`) |
| PDF | ReportLab (`entrevista_function.py`) |
| Planilhas | `openpyxl` (exportação XLSX) |
| Armazenamento | AWS S3 (`boto3`) |
| E-mail | AWS SES (`boto3`) |
| Mensageria | Meta WhatsApp Cloud API (`requests`) |

---

## 2. Arquitetura e Interligação dos Módulos

A arquitetura segue um padrão de **3 camadas lógicas**:

```
                 ┌───────────────────────────────────────┐
  Navegador ───► │  app_flask.py  (Controller / Rotas)    │
                 │  - sessão, timeout, decorators         │
                 │  - @login_required / @perfil_required  │
                 └────────────┬──────────────────────────┘
                              │ chama funções de "serviço"
        ┌─────────────────────┼─────────────────────────────────────┐
        ▼            ▼        ▼          ▼           ▼              ▼
 auth_functions  cadastro  aldeeiros  formacao   presenca      dados_function
 entrevista_function     whatsapp_function     download_s3_function
        │            │        │          │           │              │
        └────────────┴────────┴────┬─────┴───────────┴──────────────┘
                                   ▼
                    ┌──────────────────────────────┐
                    │      database_function.py    │  ← ÚNICO ponto de acesso a SQL
                    │  pool de conexões + cache    │
                    └──────────────┬───────────────┘
                                   ▼
                              MySQL (db_aldeias)

  Integrações externas:
   auth_functions ──► AWS SES (código de recuperação de senha)
   download_s3_function ──► AWS S3 (arquivos das equipes)
   whatsapp_function ──► Meta WhatsApp Cloud API
   entrevista_function ──► ReportLab (PDF em memória, sem persistência)
```

### Regras de dependência

1. **Somente `database_function.py` executa SQL.** Todos os demais módulos importam funções dele — nenhum módulo abre conexão por conta própria.
2. Os módulos de serviço (`*_function.py`) **não conhecem Flask**: não usam `request`, `session` nem `render_template`. Eles recebem um `dict` (`body`/`filtros`) e devolvem um `dict` no formato:
   ```python
   {"statusCode": 200|400|401|500, "body": json.dumps({...})}
   ```
   Esse contrato é herança de um desenho original de *AWS Lambda handlers* — por isso o `app_flask.py` sempre faz `json.loads(result["body"])`.
3. `app_flask.py` é o único responsável por sessão, autorização, flash messages e escolha de template.

---

## 3. Módulos — Responsabilidades e Integração com o Banco

### 3.1 `database_function.py` — Camada de Dados

Núcleo de acesso a dados. Responsabilidades:

- **Pool de conexões** (`_get_pool`): `PooledDB` sobre `pymysql`, `maxconnections=10`, `mincached=2`, `maxcached=5`, `cursorclass=DictCursor`. Credenciais via variáveis de ambiente `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
- **Cache em memória** (`_cache_get`, `_cache_set`, `invalidar_cache`): TTL de **300s (5 min)**. Usado para dados quase estáticos (`nucleos`, `nucleos_ativos`, equipes, aldeias). É invalidado explicitamente ao cadastrar/atualizar núcleo.
- Todas as funções usam **queries parametrizadas** (`%s`) e `finally: connection.close()` (devolve ao pool).

Principais grupos de funções e tabelas que tocam:

| Grupo | Funções | Tabelas |
|---|---|---|
| Aldeeiro | `get_aldeeiro_por_email`, `get_aldeeiro_relacoes`, `buscar_aldeeiro_por_cpf_db`, `buscar_aldeeiro_status_por_cpf`, `ativar_desativar_aldeeiro_db`, `inserir_atualizar_aldeeiro`, `select_aldeeiros_by` | `tb_aldeeiro`, `tb_aldeeiro_aldeia_fez`, `tb_aldeeiro_aldeia_serviu` |
| Perfil | `get_perfil_usuario`, `get_perfis`, `adicionar_remover_perfis` | `tb_perfil`, `tb_aldeeiro_perfil` |
| Formação | `get_formacoes`, `get_formacoes_por_nucleo`, `get_formacoes_ativas_hoje`, `insert_formacao_db`, `encerrar_formacao_db`, `consultar_formacoes_db`, `get_formacao_por_id`, `contar_formacoes_nucleo` | `tb_formacao` |
| Presença | `verificar_presenca_existente`, `inserir_presenca`, `get_presentes_por_formacao`, `relatorio_presenca_db` | `tb_frequencia_aldeeiro`, `tb_formacao`, `tb_aldeeiro` |
| Núcleo | `select_nucleos`, `select_nucleos_ativos`, `buscar_nucleo_por_id`, `cadastrar_atualizar_nucleo`, `get_info_nucleo` | `tb_nucleo` |
| Aldeias | `select_aldeias`, `select_equipes`, `consultar_aldeias_db`, `get_serventes_aldeia` | `tb_aldeia`, `tb_equipes`, `tb_aldeeiro_aldeia_*` |
| Usuário/Auth | `buscar_usuario_por_email`, `buscar_usuario_id_por_email`, inserção de usuário, gravação/validação de código | `tb_usuario`, `tb_recuperacao_senha` |
| WhatsApp | `obter_numeros_telefone` | `tb_aldeeiro` |

---

### 3.2 `auth_functions.py` — Autenticação e Recuperação de Senha

- `cadastrar_usuario_fn(body)` → cria registro em **`tb_usuario`** com `senha_hash` (`generate_password_hash`). E-mail é único (`uq_usuario_email`).
- `login(body)` → busca por e-mail e valida com `check_password_hash`. Retorna `statusCode 200` + objeto `usuario`, ou `401`.
- `solicitar_recuperacao(body)` → gera código de **6 dígitos**, grava em **`tb_recuperacao_senha`** e envia por **AWS SES** (`EMAIL_REMETENTE`, `AWS_REGION`). Validade de **10 minutos**.
- `confirmar_recuperacao(body)` → valida código não usado e dentro da validade, atualiza `tb_usuario.senha_hash` e marca `usado = 1`.

**Ponto de integração importante:** `tb_usuario` e `tb_aldeeiro` são tabelas **separadas** e a ligação entre elas é feita **pelo e-mail** (`tb_usuario.email` ↔ `tb_aldeeiro.email`). Consequência: um usuário recém-criado que ainda não preencheu o cadastro de aldeeiro **não possui perfis nem núcleo**, e por isso fica restrito às funções básicas.

---

### 3.3 `cadastro_function.py` — Cadastro/Atualização de Aldeeiro

- `salvar_aldeeiro(form_data)` → delega a `inserir_atualizar_aldeeiro` (UPSERT em `tb_aldeeiro` por CPF).
- Grava também os vínculos históricos em `tb_aldeeiro_aldeia_fez` e `tb_aldeeiro_aldeia_serviu` (aldeia, data, núcleo e, no caso de serviço, a equipe).
- O `app_flask.py` **força** `form_data['email']` com o e-mail da sessão — evita que o usuário cadastre outra pessoa no próprio login.
- Após salvar com sucesso, a rota **recarrega `session['perfil']`** (pois só após existir o aldeeiro é possível ter perfis).

---

### 3.4 `aldeeiros_function.py` — Pesquisa de Aldeeiros

- `pesquisar_aldeeiros(filtros)` → filtros de `nome`, `nucleo`, `sexo` aplicados no SQL (`select_aldeeiros_by`).
- `agrupar_aldeeiros(rows)` → consolida linhas duplicadas geradas pelos JOINs de histórico.
- `decimal_serializer` → converte `Decimal` (ids de `tb_aldeia`) e datas para JSON.
- Os filtros **por aldeia feita / aldeia servida / equipe / “nunca serviu”** são aplicados **em Python**, dentro da rota `/pesquisarAldeeiros`, usando `get_aldeeiro_relacoes(cpf)` por registro.

---

### 3.5 `dados_function.py` — Dados de Apoio (combos)

- `get_dados_aldeias()` → devolve em um único payload: `equipes`, `aldeias_fez`, `aldeias_serviu`, `nucleos`.
- Consumido por praticamente todas as telas com `<select>` (cadastro, entrevista, consultas, cabanas, arquivos).
- Se beneficia diretamente do cache de 5 minutos da camada de dados.

---

### 3.6 `formacao_function.py` — Abertura de Formação

- `abrir_formacao(body)` → insere em **`tb_formacao`** com `data_formacao = hoje`, `nucleo`, `tema`, `cpf_formador` e `ativo = 1`.
- Trata `IntegrityError 1062` contra a constraint `uq_formacao_nucleo_data (tema, nucleo, data_formacao)` → mensagem amigável “Já existe uma formação com esse tema nesse núcleo na data de hoje.”
- **Encerramento** (`encerrar_formacao_db`, chamado direto pela rota): marca `ativo = 0`. Regra: apenas formações **do dia** podem ser encerradas e, se o usuário **não for Fundador**, o `cpf_formador` é usado no `WHERE` — ou seja, **só quem abriu pode encerrar**.

---

### 3.7 `presenca_function.py` — Registro de Presença

- `registrar_presenca(body)`:
  1. `verificar_presenca_existente(cpf, id_formacao)` → bloqueia duplicidade com erro `400`.
  2. `inserir_presenca(...)` → grava em **`tb_frequencia_aldeeiro`**.
- Proteção adicional no banco: `uq_freq_formacao_aldeeiro (id_formacao, cpf_aldeeiro)`.
- O CPF **não vem do formulário quando o usuário está cadastrado** — é resolvido a partir do e-mail da sessão (`get_aldeeiro_por_email`), impedindo marcar presença por terceiros.

---

### 3.8 `entrevista_function.py` — Geração de PDFs

- `gerar_pdf_entrevista(d)` e `gerar_pdf_ficha_visitacao(d)` → constroem PDFs com ReportLab em `BytesIO`.
- Helpers `_s`, `_sim_nao`, `_radio` formatam campos do formulário.
- A rota `/entrevista/finalizar` preenche automaticamente `nome_entrevistador` (sessão), `data_entrevista` (hoje) e `telefone_entrevistador` (do aldeeiro logado), empacota os **dois PDFs em um ZIP** e envia como download.
- **Não há persistência em banco** deste módulo — a ficha é um artefato gerado sob demanda.

---

### 3.9 `download_s3_function.py` — Arquivos Informativos

- `_get_s3_client()` → cliente boto3 (`AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).
- `listar_arquivos(equipe)` → `list_objects_v2` com prefixo **`Equipes/{equipe}/`**; devolve nome, `s3_key`, tamanho e data de modificação.
- `download_arquivo_s3(s3_key)` → `get_object`, retorna buffer + `content_type`; trata `NoSuchKey` como `404`.
- Bucket configurável por `S3_BUCKET_NAME` (default `aldeias-arquivos`).
- A lista de equipes exibida na tela vem do **banco** (`tb_equipes`), e os arquivos vêm do **S3** — a integração é feita pelo **nome da equipe**.

---

### 3.10 `whatsapp_function.py` — Comunicação em Massa

- `enviar_whatsapp(body)` → obtém a lista de destinatários com `obter_numeros_telefone()` (**`tb_aldeeiro.telefone`**) e escolhe o modo:
  - `enviar_whatsapp_em_massa(numeros, mensagem)` — mensagem de texto livre;
  - `enviar_via_template(numeros, template_name, parametros)` — template aprovado na Meta, com parâmetros posicionais.
- Usa `META_PHONE_NUMBER_ID` e `META_ACCESS_TOKEN`; retorna contagem de `total`, `enviadas` e `falhas`.

---

### 3.11 `app_flask.py` — Controller Web

Responsabilidades transversais:

- **Sessão**: `permanent_session_lifetime = 10 min`; `before_request` (`check_session_timeout`) expira a sessão após **600 s de inatividade** e renova `last_activity` a cada requisição. Rotas públicas isentas: `login_page`, `cadastro_page`, `recuperar_senha_page`, `confirmar_codigo_page`, `static`.
- **`/keepalive`**: endpoint chamado por JS para manter a sessão viva em telas de preenchimento longo.
- **Decorators**:
  - `@login_required` — exige `session['usuario_id']`.
  - `@perfil_required(*perfis)` — autorização **OR**: basta possuir **um** dos perfis listados.
- **`_get_nucleo_usuario()`** — retorna `(nucleo_id, is_fundador)`; base da regra de **escopo por núcleo** nas consultas e relatórios.
- **`/exportar/xlsx`** — recebe `headers` e `rows` em JSON vindos da tabela renderizada e devolve um `.xlsx` formatado (openpyxl). É genérico e reutilizado por várias telas.
- Conteúdo da sessão: `usuario_id`, `usuario_nome`, `usuario_email`, `perfil` (lista de strings), `last_activity`.

---

## 4. Modelo de Dados

### Tabelas

| Tabela | Finalidade | Relacionamentos |
|---|---|---|
| `tb_usuario` | Credenciais de acesso (login/senha hash) | — (liga a `tb_aldeeiro` por e-mail, sem FK) |
| `tb_recuperacao_senha` | Códigos de recuperação de senha | FK → `tb_usuario` (CASCADE) |
| `tb_aldeeiro` | Dados pessoais e endereço do membro (PK = `cpf`) | FK `nucleo` → `tb_nucleo` |
| `tb_nucleo` | Núcleos regionais; `ativo_relatorio` controla exibição | — |
| `tb_perfil` | Catálogo de perfis (id 1..10) | — |
| `tb_aldeeiro_perfil` | N:N aldeeiro × perfil | FKs → `tb_aldeeiro` (CASCADE), `tb_perfil` (RESTRICT) |
| `tb_aldeia` | Tipos de aldeia (eventos) | — |
| `tb_equipes` | Equipes de serviço e suas funções | — |
| `tb_aldeeiro_aldeia_fez` | Aldeias que o membro **participou** | FKs → aldeeiro, aldeia, núcleo · UNIQUE (cpf, id_aldeia) |
| `tb_aldeeiro_aldeia_serviu` | Aldeias em que o membro **serviu** | FKs → aldeeiro, aldeia, equipe, núcleo |
| `tb_formacao` | Encontro de formação (tema, data, núcleo, formador, ativo) | FKs → núcleo, formador · UNIQUE (tema, núcleo, data) |
| `tb_frequencia_aldeeiro` | Presença do membro na formação | FKs → formação, aldeeiro · UNIQUE (id_formacao, cpf) |

### Diagrama simplificado

```
tb_usuario ---(email)--- tb_aldeeiro ──┬── tb_nucleo
     │                      │          │
tb_recuperacao_senha        │          ├── tb_aldeeiro_perfil ── tb_perfil
                            │          │
                            │          ├── tb_aldeeiro_aldeia_fez ── tb_aldeia
                            │          │
                            │          └── tb_aldeeiro_aldeia_serviu ── tb_aldeia
                            │                                        └── tb_equipes
                            │
                            └── tb_frequencia_aldeeiro ── tb_formacao ── tb_nucleo
                                                              └── (cpf_formador)
```

### Integridade e performance

- **UNIQUEs** de negócio: 1 formação por (tema, núcleo, dia); 1 presença por (formação, aldeeiro); 1 registro por (aldeeiro, aldeia feita).
- **ON DELETE CASCADE** em vínculos do aldeeiro; **RESTRICT** em `tb_perfil` (impede excluir perfil em uso).
- **Índices** criados para `nome`, `cidade/uf`, `id_formacao`, `cpf_aldeeiro`, `nucleo`, `data_formacao`, equipe e perfil.
- O sistema **não deleta aldeeiros** — usa `ativo = 0` (soft delete via ativar/desativar).

---

## 5. Perfis de Usuário e Permissões

### Perfis cadastrados (`tb_perfil`)

| ID | Perfil | Descrição funcional |
|---|---|---|
| 1 | **Aldeeiro** | Perfil base de todo membro cadastrado |
| 2 | **Formador** | Abre e encerra formações do seu núcleo |
| 3 | **Coordenador** | Gestão e consultas no escopo do seu núcleo |
| 4 | **Administrador** | Gestão de perfis, núcleos e status de cadastro |
| 5 | **Fundador** | Acesso irrestrito a todos os núcleos |
| 6 | **Usuário** | Perfil de leitura ampliada de relatórios de presença |
| — | **Colegiado** | Referenciado no código (`relatorio_presenca`), **mas não inserido no script SQL** — precisa ser criado manualmente (id 7) |

> Um mesmo CPF pode acumular vários perfis (`tb_aldeeiro_perfil` é N:N) — a autorização é sempre **OR**.

### Matriz de permissões por funcionalidade

| Funcionalidade | Rota | Perfis exigidos |
|---|---|---|
| Login / Cadastro / Recuperar senha | `/login`, `/cadastro`, `/recuperar-senha`, `/confirmar-codigo` | Público |
| Página inicial | `/init-aldeias` | Autenticado |
| Meu cadastro de aldeeiro | `/aldeeiro/form`, `/salvar_atualizar_aldeeiro` | Autenticado |
| Informações gerais dos núcleos | `/informacoes`, `/api/info-nucleo` | Autenticado |
| Registrar presença | `/formacao/presenca` | Autenticado |
| Formações por núcleo (API) | `/api/formacoes` | Autenticado |
| Ficha de entrevista (PDF/ZIP) | `/entrevista`, `/entrevista/finalizar` | Autenticado |
| Arquivos informativos / download | `/arquivos`, `/arquivos/download` | Autenticado |
| Organizar cabanas | `/cabanas/organizar` | Autenticado |
| Exportar XLSX | `/exportar/xlsx` | Autenticado |
| Manter sessão | `/keepalive` | Autenticado |
| **Abrir formação** | `/formacao/abrir` | Formador, Fundador |
| **Encerrar formação** | `/formacao/encerrar/<id>` | Formador (só a própria), Fundador |
| **Listar/pesquisar aldeeiros** | `/aldeeiro/listar`, `/pesquisarAldeeiros` | Coordenador, Fundador |
| **Detalhar aldeeiro** | `/aldeeiro/detalhar/<cpf>` | Coordenador, Fundador |
| **Consultar formações** | `/formacao/consultar` | Coordenador, Fundador |
| **Consultar aldeias** | `/aldeia/consultar` | Coordenador, Fundador |
| **Serventes de uma aldeia** | `/aldeia/serventes` | Coordenador, Fundador |
| **Lista de presentes** | `/formacao/<id>/presentes` | Coordenador, Fundador |
| **Envio WhatsApp em massa** | `/whatsapp/enviar` | Coordenador, Fundador |
| **Relatório de presença** | `/relatorio/presenca` | Coordenador, Usuário, Fundador, Colegiado |
| **Gerenciar perfis** | `/admin/perfis` | Administrador, Fundador |
| **Ativar/desativar aldeeiro** | `/admin/ativar-desativar` | Administrador, Fundador |
| **Cadastrar/atualizar núcleo** | `/admin/cadastrar-nucleo` | Administrador, Fundador |
| **Buscas administrativas** | `/admin/buscar-aldeeiro`, `/admin/buscar-aldeeiro-status`, `/admin/buscar-nucleo` | Administrador, Fundador |

### Regras de escopo (além do perfil)

1. **Escopo por núcleo** — em `consultar_formacoes`, `consultar_aldeias` e `relatorio_presenca`, se o usuário **não** for Fundador (ou, no relatório, não for `Usuário`/`Colegiado`), o filtro de núcleo é **sobrescrito** pelo núcleo do próprio aldeeiro. Ele não consegue consultar outro núcleo mesmo manipulando o formulário.
2. **Formador só encerra a própria formação** — `encerrar_formacao_db` recebe `cpf_formador` quando o usuário não é Fundador.
3. **Autoproteção administrativa** — o Administrador **não pode alterar o próprio perfil** nem **ativar/desativar o próprio cadastro** (`gerenciar_perfis`, `ativar_desativar_aldeeiro`).
4. **Presença só para si** — o CPF usado no registro de presença vem do aldeeiro vinculado ao e-mail logado.
5. **Formações filtradas pelo núcleo do membro** — na tela de presença, `get_formacoes_por_nucleo(nucleo_aldeeiro)`.
6. **Menu condicionado** — `templates/index.html` esconde os cards conforme `session['perfil']`; a checagem real, porém, é feita no servidor pelos decorators.

---

## 6. Fluxos Principais

### 6.1 Onboarding
```
/cadastro → tb_usuario (senha_hash)
   → /login → sessão criada + get_perfil_usuario(email)
   → /aldeeiro/form → salvar_aldeeiro → tb_aldeeiro (+ aldeia_fez / aldeia_serviu)
   → session['perfil'] recarregado
   → Administrador concede perfis em /admin/perfis → tb_aldeeiro_perfil
```
Enquanto não existir registro em `tb_aldeeiro` para aquele e-mail, `session['perfil']` fica vazio e o usuário vê apenas as funções básicas.

### 6.2 Formação e Presença
```
Formador → /formacao/abrir → insert_formacao_db → tb_formacao (ativo=1, data=hoje)
Aldeeiro → /formacao/presenca → verificar_presenca_existente → inserir_presenca
                                              → tb_frequencia_aldeeiro
Formador → /formacao/encerrar/<id> → ativo=0
Coordenador → /formacao/<id>/presentes  e  /relatorio/presenca
```

### 6.3 Recuperação de Senha
```
/recuperar-senha → solicitar_recuperacao → código 6 dígitos → tb_recuperacao_senha
                                         → AWS SES envia e-mail
/confirmar-codigo → confirmar_recuperacao → valida (10 min, usado=0)
                                          → UPDATE tb_usuario.senha_hash, usado=1
```

### 6.4 Arquivos Informativos
```
/arquivos → tb_equipes (lista de equipes)
          → listar_arquivos(equipe) → S3 prefix "Equipes/{equipe}/"
/arquivos/download?s3_key=... → download_arquivo_s3 → send_file
```

---

## 7. Configuração e Execução

### Variáveis de ambiente

| Variável | Uso |
|---|---|
| `TEMPLATES_DIR` | Diretório dos templates Jinja2 (**obrigatória**) |
| `SECRET_KEY` | Chave de assinatura da sessão Flask (default inseguro em código) |
| `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Conexão MySQL |
| `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Credenciais AWS (S3 e SES) |
| `S3_BUCKET_NAME` | Bucket dos arquivos (default `aldeias-arquivos`) |
| `EMAIL_REMETENTE` | Remetente verificado no SES |
| `META_PHONE_NUMBER_ID`, `META_ACCESS_TOKEN` | WhatsApp Cloud API |

### Passos

```powershell
pip install -r requirements.txt
# criar a base
mysql -u root -p < db\db_aldeiasV1.sql
# definir variáveis de ambiente e executar
python application\app_flask.py
```

> `app_flask.py` chama `application.run(debug=True)` no final do arquivo. Em produção isso deve ser substituído por um WSGI (Gunicorn/uWSGI) com `debug=False`.

---

## 8. Observações Técnicas e Pontos de Atenção

1. **Perfil `Colegiado` inexistente no seed** — referenciado em `/relatorio/presenca`, mas ausente do `INSERT INTO tb_perfil`. Adicionar `(7,'Colegiado')`.
2. **`SECRET_KEY` com valor default hardcoded** — deve ser obrigatoriamente definida por ambiente.
3. **`debug=True` no código** — risco de exposição do console interativo Werkzeug.
4. **Vínculo `tb_usuario` ↔ `tb_aldeeiro` apenas por e-mail**, sem FK; `tb_aldeeiro.email` tem limite de 30 caracteres enquanto `tb_usuario.email` tem 100 — e-mails longos quebram o vínculo.
5. **Filtros de aldeia/equipe em Python** (`/pesquisarAldeeiros`) executam uma query por aldeeiro (N+1) — candidato natural a otimização via SQL.
6. **Cache global em memória** — funciona apenas em processo único; com múltiplos workers cada um terá seu próprio cache (TTL de 5 min limita a divergência).
7. **Rotas `/aldeeiro/listar` e `/pesquisarAldeeiros` passam `is_fundador=True` fixo** ao template, ignorando o escopo de núcleo do Coordenador nessa tela específica.
8. **Timeout curto (10 min)** mitigado pelo endpoint `/keepalive`.

