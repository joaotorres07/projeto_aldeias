# Estimativa de Custo AWS — Sistema Aldeias

> Documento gerado em 24/04/2026 | Baseado na análise completa do projeto
> **Região AWS:** `us-east-1` (N. Virginia) — região mais barata da AWS
> **Câmbio:** 1 USD = R$ 5,00

---

## Visão Geral do Projeto

| Item | Detalhes |
|---|---|
| **Aplicação** | Flask (Python) com Jinja2 server-side rendering |
| **Banco de Dados** | MySQL 8.0 — 12 tabelas |
| **Autenticação** | Sessão Flask + bcrypt + recuperação de senha via email |
| **Arquivos** | S3 Bucket para download de arquivos por equipe |
| **Email** | AWS SES para envio de códigos de recuperação de senha (futuro: validação de cadastro) |
| **Templates HTML** | 20 páginas responsivas com Bootstrap 5 |
| **Módulos Python** | 10 arquivos backend (app_flask, database_function, auth_functions, etc.) |
| **Relatórios** | Paginação client-side + exportação XLSX (openpyxl) |
| **Perfis** | 6 perfis (Aldeeiro, Formador, Coordenador, Administrador, Usuário, Fundador) |

### Premissas de Uso

| Métrica | Valor |
|---|---|
| Total de usuários cadastrados | ~50.000 |
| Acessos semanais (registro de presença) | ~1.000 por semana |
| Pico de acessos simultâneos | ~100-200 |
| Relatórios/consultas por semana | ~50 |
| Formações abertas por semana | ~10-15 |
| Emails enviados por mês (recuperação de senha) | ~100 |
| Arquivos no S3 | ~20 arquivos de texto (~1 MB total) |
| Tamanho estimado do banco de dados | ~500 MB (crescendo ~100 MB/ano) |

---

## Recursos AWS Necessários

| Serviço | Finalidade |
|---|---|
| **EC2** | Hospedar a aplicação Flask + Gunicorn + Nginx |
| **RDS MySQL** | Banco de dados relacional |
| **S3** | Armazenamento de arquivos para download |
| **SES** | Envio de emails (recuperação de senha, futuro: validação de cadastro) |
| **Elastic IP** | IP fixo para o EC2 |
| **CloudWatch** | Logs e monitoramento básico |

> ⚠️ **Nota sobre a região:** `us-east-1` (N. Virginia) é em média **30-40% mais barata** que `sa-east-1` (São Paulo). A desvantagem é a latência maior (~120ms vs ~20ms), porém para o perfil de uso deste sistema (acessos semanais, sem requisito de tempo real) o impacto é imperceptível.

---

## Cenário 1: Recursos Básicos (Menor Custo) 💰

> Ideal para início de operação, validação e primeiros meses

### Especificações

| Serviço | Tipo/Config | Detalhes |
|---|---|---|
| **EC2** | `t3.micro` (2 vCPU, 1 GB RAM) | Amazon Linux 2023, EBS 20 GB gp3 |
| **RDS MySQL** | `db.t3.micro` (2 vCPU, 1 GB RAM) | 20 GB gp3, Single-AZ, sem backup automático |
| **S3** | Standard | ~1 MB armazenado, ~1.000 GETs/mês |
| **SES** | Pay-per-use | ~100 emails/mês |
| **Elastic IP** | 1 IP | Vinculado ao EC2 (sem custo extra se em uso) |
| **CloudWatch** | Free Tier | Logs básicos, métricas padrão |
| **Data Transfer** | ~10 GB saída/mês | Inclui páginas HTML + downloads S3 |

### Estimativa Mensal — Recursos Básicos

| Serviço | Cálculo | USD/mês | BRL/mês |
|---|---|---|---|
| EC2 t3.micro | 730h × $0.0104/h | **$7.59** | **R$ 37,95** |
| EBS 20 GB gp3 | 20 GB × $0.08/GB | **$1.60** | **R$ 8,00** |
| RDS db.t3.micro | 730h × $0.017/h | **$12.41** | **R$ 62,05** |
| RDS Storage 20 GB | 20 GB × $0.115/GB | **$2.30** | **R$ 11,50** |
| S3 Storage | ~1 MB × $0.023/GB | **$0.01** | **R$ 0,05** |
| S3 Requests | ~1.000 GETs × $0.0004/1K | **$0.01** | **R$ 0,05** |
| SES | 100 emails × $0.10/1000 | **$0.01** | **R$ 0,05** |
| Elastic IP | Em uso = grátis | **$0.00** | **R$ 0,00** |
| Data Transfer | 10 GB × $0.09/GB | **$0.90** | **R$ 4,50** |
| CloudWatch | Free Tier | **$0.00** | **R$ 0,00** |
| **TOTAL MENSAL** | | **$24.83** | **R$ 124,15** |
| **TOTAL ANUAL** | | **$297.96** | **R$ 1.489,80** |

> 💡 **Com Free Tier (12 primeiros meses):** EC2 t3.micro e RDS db.t3.micro são elegíveis → **~$2.92/mês (R$ 14,60/mês)** → **~$35.04/ano (R$ 175,20/ano)**

### Limitações do Cenário Básico

- ⚠️ `t3.micro` com 1 GB RAM pode ficar apertado com >100 conexões simultâneas
- ⚠️ Single-AZ no RDS — se a instância cair, o banco fica offline
- ⚠️ Sem backup automático — risco de perda de dados
- ⚠️ Sem HTTPS nativo — precisa configurar Let's Encrypt manualmente
- ⚠️ Sem redundância — único ponto de falha
- ⚠️ Latência ~120ms por estar em us-east-1 (imperceptível para o uso)

---

## Cenário 2: Recursos Intermediários (Recomendado para Produção) ⭐

> Equilibra custo e confiabilidade para 50K usuários com acessos semanais

### Especificações

| Serviço | Tipo/Config | Detalhes |
|---|---|---|
| **EC2** | `t3.small` (2 vCPU, 2 GB RAM) | Amazon Linux 2023, EBS 30 GB gp3 |
| **RDS MySQL** | `db.t3.small` (2 vCPU, 2 GB RAM) | 30 GB gp3, Single-AZ, backup 7 dias |
| **S3** | Standard | ~1 MB armazenado, ~2.000 GETs/mês |
| **SES** | Pay-per-use | ~200 emails/mês |
| **Elastic IP** | 1 IP | Vinculado ao EC2 |
| **CloudWatch** | Logs + Alarmes | 10 GB logs, 2 alarmes |
| **Data Transfer** | ~20 GB saída/mês | |
| **ACM + ALB** | Certificado SSL grátis + Load Balancer | HTTPS automático |

### Estimativa Mensal — Recursos Intermediários

| Serviço | Cálculo | USD/mês | BRL/mês |
|---|---|---|---|
| EC2 t3.small | 730h × $0.0208/h | **$15.18** | **R$ 75,90** |
| EBS 30 GB gp3 | 30 GB × $0.08/GB | **$2.40** | **R$ 12,00** |
| RDS db.t3.small | 730h × $0.034/h | **$24.82** | **R$ 124,10** |
| RDS Storage 30 GB | 30 GB × $0.115/GB | **$3.45** | **R$ 17,25** |
| RDS Backup 30 GB | 30 GB × $0.095/GB | **$2.85** | **R$ 14,25** |
| S3 Storage + Requests | ~1 MB + 2K GETs | **$0.02** | **R$ 0,10** |
| SES | 200 emails | **$0.02** | **R$ 0,10** |
| Elastic IP | Em uso | **$0.00** | **R$ 0,00** |
| ALB | 730h × $0.0225/h + LCU | **$18.44** | **R$ 92,20** |
| ACM (SSL) | Gratuito com ALB | **$0.00** | **R$ 0,00** |
| Data Transfer | 20 GB × $0.09/GB | **$1.80** | **R$ 9,00** |
| CloudWatch | 10 GB logs + 2 alarmes | **$5.30** | **R$ 26,50** |
| **TOTAL MENSAL** | | **$74.28** | **R$ 371,40** |
| **TOTAL ANUAL** | | **$891.36** | **R$ 4.456,80** |

### Benefícios adicionais

- ✅ 2 GB RAM — confortável para 200 conexões simultâneas
- ✅ Backup automático do banco (7 dias de retenção)
- ✅ HTTPS com certificado gratuito via ACM
- ✅ ALB permite futuro auto scaling
- ✅ CloudWatch com alarmes para CPU/memória

---

## Cenário 3: Recursos Premium (Alta Disponibilidade) 🏢

> Para máxima confiabilidade, zero downtime e crescimento acelerado

### Especificações

| Serviço | Tipo/Config | Detalhes |
|---|---|---|
| **EC2** | `t3.medium` (2 vCPU, 4 GB RAM) × 2 instâncias | Multi-AZ com Auto Scaling Group |
| **RDS MySQL** | `db.t3.medium` (2 vCPU, 4 GB RAM) | 50 GB gp3, Multi-AZ, backup 30 dias |
| **S3** | Standard + Versionamento | ~1 MB + versionamento habilitado |
| **SES** | Pay-per-use | ~500 emails/mês |
| **ALB** | Application Load Balancer | Distribui entre 2 EC2s |
| **ACM** | Certificado SSL | Gratuito |
| **CloudWatch** | Logs + Alarmes + Dashboard | 20 GB logs, 5 alarmes, 1 dashboard |
| **WAF** | Web Application Firewall | Proteção contra ataques comuns |
| **Data Transfer** | ~50 GB saída/mês | |

### Estimativa Mensal — Recursos Premium

| Serviço | Cálculo | USD/mês | BRL/mês |
|---|---|---|---|
| EC2 t3.medium × 2 | 2 × 730h × $0.0416/h | **$60.74** | **R$ 303,70** |
| EBS 30 GB gp3 × 2 | 2 × 30 GB × $0.08/GB | **$4.80** | **R$ 24,00** |
| RDS db.t3.medium Multi-AZ | 730h × $0.136/h | **$99.28** | **R$ 496,40** |
| RDS Storage 50 GB | 50 GB × $0.115/GB | **$5.75** | **R$ 28,75** |
| RDS Backup 50 GB | 50 GB × $0.095/GB | **$4.75** | **R$ 23,75** |
| S3 + Versionamento | ~2 MB + 5K GETs | **$0.03** | **R$ 0,15** |
| SES | 500 emails | **$0.05** | **R$ 0,25** |
| ALB | 730h × $0.0225/h + LCU | **$22.00** | **R$ 110,00** |
| ACM (SSL) | Gratuito | **$0.00** | **R$ 0,00** |
| WAF | $5 base + $1/regra × 3 regras | **$8.00** | **R$ 40,00** |
| CloudWatch | 20 GB logs + 5 alarmes + dashboard | **$12.50** | **R$ 62,50** |
| Data Transfer | 50 GB × $0.09/GB | **$4.50** | **R$ 22,50** |
| **TOTAL MENSAL** | | **$222.40** | **R$ 1.112,00** |
| **TOTAL ANUAL** | | **$2,668.80** | **R$ 13.344,00** |

### Benefícios adicionais

- ✅ Multi-AZ no EC2 e RDS — zero downtime em caso de falha de uma zona
- ✅ Auto Scaling — escala automaticamente com demanda
- ✅ WAF — proteção contra SQL injection, XSS, DDoS básico
- ✅ 4 GB RAM por instância — suporta picos de 500+ conexões
- ✅ Backup de 30 dias — recuperação de qualquer ponto no tempo
- ✅ Versionamento S3 — histórico de todas as alterações de arquivos

---

## Comparativo dos 3 Cenários

| Critério | Básico | Intermediário | Premium |
|---|---|---|---|
| **Custo mensal (USD)** | ~$25 | ~$74 | ~$222 |
| **Custo mensal (BRL)** | ~R$ 124 | ~R$ 371 | ~R$ 1.112 |
| **Custo anual (USD)** | ~$298 | ~$891 | ~$2,669 |
| **Custo anual (BRL)** | ~R$ 1.490 | ~R$ 4.457 | ~R$ 13.344 |
| **RAM total** | 1 GB | 2 GB | 8 GB (2×4) |
| **Conexões simultâneas** | ~50-100 | ~200 | ~500+ |
| **Disponibilidade** | ~99% | ~99.5% | ~99.9% |
| **Backup** | ❌ Manual | ✅ 7 dias | ✅ 30 dias |
| **HTTPS** | ⚠️ Let's Encrypt | ✅ ACM + ALB | ✅ ACM + ALB |
| **Redundância** | ❌ Nenhuma | ⚠️ Parcial | ✅ Total (Multi-AZ) |
| **Proteção WAF** | ❌ | ❌ | ✅ |
| **Auto Scaling** | ❌ | ⚠️ Manual | ✅ Automático |
| **Migração entre cenários** | — | ~30 min | ~1 hora |

---

## Serviços Futuros (Após criação da conta AWS)

### AWS SES (Simple Email Service)

| Etapa | Ação |
|---|---|
| **Sandbox** | Por padrão, SES começa em modo sandbox (só envia para emails verificados) |
| **Verificar domínio** | Adicionar registros DNS (DKIM + SPF) para o domínio do projeto |
| **Solicitar produção** | Abrir ticket na AWS para sair do sandbox → envio para qualquer email |
| **Custo** | $0.10 por 1.000 emails (R$ 0,50/1.000 emails) — ~R$ 0,05/mês para o uso atual |

**Funcionalidades que dependem do SES:**
- Recuperação de senha (já implementado)
- Validação de email no cadastro (planejado — ver `PLANO_VALIDACAO_EMAIL.md`)

### AWS S3 (Simple Storage Service)

| Etapa | Ação |
|---|---|
| **Criar bucket** | Nome: `aldeias-arquivos`, Região: `us-east-1` |
| **Bloquear acesso público** | Manter 100% privado |
| **Estrutura de pastas** | `equipes/banda/`, `equipes/cozinha/`, `equipes/lideranca-mediadores/` |
| **IAM Role** | EC2 com policy `AmazonS3ReadOnlyAccess` |
| **Custo** | ~$0.023/GB/mês (R$ 0,12/GB/mês) + $0.0004/1000 GETs — ~R$ 0,10/mês |

**Funcionalidades que dependem do S3:**
- Download de arquivos informativos por equipe (já implementado — `download_s3_function.py`)

---

## Recomendação

```
📊 Para início de operação:
   → Cenário 1 (Básico) com Free Tier = ~$3/mês (R$ 15/mês) por 12 meses

📊 Para produção com 50K usuários:
   → Cenário 2 (Intermediário) = ~$74/mês (R$ 371/mês)
   → Melhor custo-benefício com backup, HTTPS e monitoramento

📊 Para crescimento acelerado ou exigência de SLA:
   → Cenário 3 (Premium) = ~$222/mês (R$ 1.112/mês)
   → Só necessário se houver requisito de 99.9% de disponibilidade
```

### Caminho de Evolução Recomendado

```
Mês 1-12:  Básico (Free Tier)     ~R$ 15/mês     → Validar o sistema
Mês 13-24: Básico (sem Free Tier) ~R$ 124/mês    → Operação normal
Mês 25+:   Intermediário           ~R$ 371/mês    → Se acessos crescerem
Futuro:    Premium                  ~R$ 1.112/mês  → Se exigir alta disponibilidade
```

> ⚠️ **Importante:** A migração entre cenários é simples — basta alterar o tipo da instância EC2/RDS (resize) que leva de 5 a 30 minutos com downtime mínimo. Não requer alteração de código.

---

## Resumo de Custos

| Cenário | USD/mês | BRL/mês | USD/ano | BRL/ano | Free Tier (1º ano) |
|---|---|---|---|---|---|
| **Básico** | $24.83 | R$ 124,15 | $297.96 | R$ 1.489,80 | ~R$ 175,20/ano |
| **Intermediário** | $74.28 | R$ 371,40 | $891.36 | R$ 4.456,80 | ~R$ 272,40/ano* |
| **Premium** | $222.40 | R$ 1.112,00 | $2,668.80 | R$ 13.344,00 | N/A |

\* *Free Tier se aplica apenas a t3.micro — o intermediário usa t3.small, mas o RDS db.t3.micro é elegível*

---

*Valores estimados em abril/2026 com base na tabela de preços AWS região us-east-1 (N. Virginia) — região mais barata. Câmbio estimado: 1 USD = R$ 5,00. Preços podem variar conforme atualizações da AWS e câmbio. Impostos locais não incluídos.*
