# 🎙️ Transcritor de Áudio do WhatsApp (FastAPI & Faster-Whisper INT8)

> **Categoria:** Nível 2 iFood — Automações com Economia Real em Processos & Nível 3 — Ferramentas Deployadas com IA  
> **Status:** Em Produção / Microsserviço Conteinerizado (Docker Compose)  
> **Impacto Mensurável:** Transcrição 100% em memória (privacidade LGPD sem persistência de áudio em disco); inferência 5x mais rápida que tempo real via Whisper INT8 local; economia de 100% em custos de APIs externas de transcrição; 39 testes automatizados com `pytest` e `uv`.

---

## 🎯 O Problema de Negócio

Em operações comerciais, suporte ao cliente e logística (como entregas e frotas de campo), o envio de mensagens de voz pelo WhatsApp é a forma primária de comunicação. No entanto, mensagens de voz geram três grandes gargalos:

1. **Perda de Produtividade na Escuta Manual:** Operadores e atendentes gastam minutos valiosos ouvindo áudios longos, gerando filas de atendimento e atrasos operacionais.
2. **Inviabilidade de Indexação e Busca:** Áudios em formato de voz proprietário do WhatsApp (`.ogg` Opus PTT) são caixas-pretas: não permitem busca por texto, número de pedido ou endereço.
3. **Custos e Riscos de Privacidade com APIs Externas:** Transmitir áudios confidenciais de clientes para APIs pagas em nuvem eleva custos de faturamento por minuto e viola diretrizes rígidas de privacidade e LGPD.

---

## 💡 A Solução Técnica

Desenvolvimento de um **microsserviço de alto desempenho em FastAPI**, integrado via webhook com a engine **Evolution Go**, que processa e responde mensagens de voz automaticamente:

- **Processamento 100% em Memória (`In-Memory Streaming`):** O áudio trafega em `BytesIO` durante o ciclo de vida da requisição e é imediatamente descartado após a inferência. Nenhum arquivo de áudio ou texto de transcrição é gravado em disco, garantindo conformidade rigorosa com a LGPD.
- **Inferência Local com Faster-Whisper (INT8):** Execução do modelo Whisper quantizado em INT8 com **CTranslate2** e **Silero VAD** diretamente em CPU. Custo zero por minuto e velocidade até 5x superior ao tempo de reprodução real.
- **Arquitetura Resiliente & Idempotência:** Repositório transacional (SQLite/PostgreSQL) para deduplicação automática de mensagens, prevenindo respostas redundantes a webhooks repetidos.
- **Suíte de Testes Automatizada com 100% de Cobertura:** 39 testes E2E e unitários com `pytest`, `pytest-asyncio` e `respx` (simulando payloads da Evolution API e do Whisper com zero chamadas externas).
- **Stack 100% Conteinerizada:** Orquestração completa via Docker Compose (`app` FastAPI + `evolution-go` WhatsApp bridge + `postgres`).

---

## 🏗️ Arquitetura do Sistema

```mermaid
flowchart TD
    subgraph Client["Usuário / Operação"]
        U["Remetente no WhatsApp<br/>(Mensagem de Voz PTT)"]
    end

    subgraph Infrastructure["Stack Docker Compose"]
        EVO["Evolution Go (Porta 4000)<br/>Ponte WhatsApp Web (whatsmeow)"]
        PG[("PostgreSQL 16<br/>Sessões e Metadados")]
        APP["Microsserviço FastAPI (Porta 8000)<br/>Python 3.12 / uv / Uvicorn"]
        
        subgraph Engine["Motor de Inferência em Memória"]
            MEM["BytesIO (Sem Gravação em Disco)"]
            VAD["Silero VAD (Detecção de Fala)"]
            WHISPER["Faster-Whisper (INT8 / CPU)"]
        end

        DB_IDEM[("SQLite Local<br/>Idempotência de Mensagens")]
    end

    U -->|Áudio OGG/Opus| EVO
    EVO <-->|Autenticação / Sessão| PG
    EVO -->|POST /webhooks/evolution (Webhook HMAC)| APP
    
    APP -->|Deduplica Mensagem| DB_IDEM
    APP -->|Buffer de Áudio| MEM
    MEM --> VAD
    VAD --> WHISPER
    WHISPER -->|Texto Transcrito em pt-BR| APP
    
    APP -->|POST /message/sendText| EVO
    EVO -->|Resposta de Texto Instantânea| U
```

---

## ⚡ Requisitos e Início Rápido

- Docker Engine e Docker Compose v2.
- Gerenciador Astral **`uv`** e Python 3.12+ (para desenvolvimento local).
- Não requer chaves pagas da OpenAI/Google: a transcrição roda 100% localmente.

### 1. Configuração do Ambiente

```bash
cp .env.example .env
```

Defina as variáveis essenciais:
- `EVOLUTION_API_KEY`: Chave de autenticação da Evolution Go.
- `WEBHOOK_SECRET`: Chave secreta compartilhada para validação do webhook.
- `POSTGRES_PASSWORD`: Senha do banco de dados das sessões.
- `WHISPER_MODEL`: Padrão `base` (ou `small`, `medium`).
- `WHISPER_DEVICE`: `cpu` e `WHISPER_COMPUTE_TYPE`: `int8`.

### 2. Execução com Docker Compose

```bash
docker compose up -d --build
docker compose ps
```

Verifique a saúde da aplicação:
```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
```
Respostas esperadas: `{"status":"ok"}` e `{"status":"ready"}`.

### 3. Conexão da Instância do WhatsApp

Crie a instância e conecte com o webhook:
```bash
# 1. Criar instância
curl -X POST http://127.0.0.1:4000/instance/create \
  -H "Content-Type: application/json" \
  -H "apikey: SUA_EVOLUTION_API_KEY" \
  -d '{"instanceName": "personal"}'

# 2. Conectar e gerar QR Code
curl -X POST http://127.0.0.1:4000/instance/connect \
  -H "Content-Type: application/json" \
  -H "apikey: SUA_EVOLUTION_API_KEY" \
  -H "instanceId: personal" \
  -d '{
    "webhookUrl": "http://app:8000/webhooks/evolution",
    "subscribe": ["MESSAGES_UPSERT"],
    "immediate": true
  }'
```

Escaneie o QR Code retornado no aplicativo do WhatsApp em **Aparelhos Conectados**.

---

## 🧪 Testes Automatizados (Suíte 100% Local)

A aplicação possui **39 testes automatizados** cobrindo autenticação, tratamento de eventos, idempotência e inferência:

```bash
# Sincronizar dependências com uv
uv sync --all-groups

# Executar a suíte de testes
uv run pytest -v

# Validação de código com Ruff
uv run ruff check .
```

---

## 🔒 Conformidade com LGPD & Segurança

- **Zero Persistência de Dados de Voz:** O áudio é lido e descartado imediatamente em memória RAM.
- **Binding Localhost:** Portas 8000 e 4000 permanecem bindadas a `127.0.0.1`, prevenindo exposição pública desnecessária.
- **Idempotência Segura:** Apenas hashes e IDs das mensagens são armazenados temporariamente para prevenir duplicidade de respostas.
