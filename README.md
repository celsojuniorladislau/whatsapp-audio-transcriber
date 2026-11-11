# Transcritor de áudio WhatsApp (Evolution API)

MVP pessoal: envie uma mensagem de voz para o número conectado; o serviço responde com a transcrição em português. O áudio é processado em memória pelo backend e não é gravado em disco. A Evolution API está fixada em `evoapicloud/evolution-api:v2.3.7`.

> **Atenção:** a Evolution API conecta via WhatsApp Web (Baileys), não é a API oficial da Meta. Há risco de desconexão, restrição ou banimento do número. Use um número dedicado e confira os termos aplicáveis. Este MVP não deve ser usado para processar mensagens de terceiros sem consentimento.

## Requisitos

- Docker Engine e Docker Compose v2
- Uma conexão de internet na primeira inicialização para baixar o modelo Whisper local.
- Um número WhatsApp dedicado para vincular à instância.
- Não é necessária chave OpenAI/GPT: a transcrição roda localmente via `faster-whisper`.

## Configuração local

```bash
cp .env.example .env
```

Edite `.env` localmente e defina:

- `EVOLUTION_API_KEY`: uma chave aleatória forte; a mesma chave autentica a API Evolution.
- `WEBHOOK_SECRET`: outro segredo forte, diferente da chave da Evolution.
- `POSTGRES_PASSWORD`: senha alfanumérica forte (para evitar problemas de escaping na URI PostgreSQL).
- `WHISPER_MODEL`, `WHISPER_DEVICE`, `WHISPER_COMPUTE_TYPE`: modelo e execução locais; padrão `base`, CPU e `int8`, sem custo por minuto/API.

Não envie esses valores por chat e não faça commit do `.env`. A API e o backend ficam bindados a `127.0.0.1`; não exponha as portas 8000/8080 diretamente à internet.

Inicie os serviços:

```bash
docker compose up -d --build
docker compose ps
```

Na primeira inicialização, `faster-whisper` baixa o modelo configurado em `WHISPER_MODEL` (padrão `base`, CPU/int8) para o volume persistente `whisper_models`. Aguarde o serviço `app` ficar `healthy`; o tempo depende da rede e do equipamento. A inferência consome CPU/RAM localmente; não há cobrança por requisição.

A aplicação deve ficar `healthy`; PostgreSQL e Redis devem ficar `healthy`, Evolution API `running`. Verifique:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
```

Respostas esperadas: `{"status":"ok"}` e `{"status":"ready"}`.

## Criar instância e vincular WhatsApp

Abra `http://127.0.0.1:8080/docs`, autorize com a chave da Evolution e use `POST /instance/create` com:

```json
{
  "instanceName": "personal",
  "integration": "WHATSAPP-BAILEYS",
  "qrcode": true,
  "webhook": {
    "enabled": true,
    "url": "http://app:8000/webhooks/evolution",
    "headers": {"x-webhook-secret": "COLOQUE_AQUI_O_WEBHOOK_SECRET_DO_ENV"},
    "byEvents": false,
    "base64": false,
    "events": ["MESSAGES_UPSERT"]
  }
}
```

Substitua o valor de `x-webhook-secret` pelo `WEBHOOK_SECRET` do `.env`, localmente no painel (não o publique). No resultado, obtenha o QR code ou consulte `GET /instance/connect/personal`; escaneie-o no WhatsApp do número dedicado em **Dispositivos conectados**. O nome `personal` precisa coincidir com `EVOLUTION_INSTANCE` no `.env`.

Se a instância já existir, configure o webhook por `POST /webhook/set/personal` usando o mesmo objeto `webhook` (sem a chave `webhook` externa, conforme schema da Evolution API v2.3.7).

## Teste ponta a ponta

De outro telefone/conta, envie uma mensagem de voz individual para o número dedicado. Deve receber `Transcrição: ...`. Mensagens próprias, grupos e conteúdo que não seja áudio são ignorados. Uma repetição do mesmo webhook não deve gerar outra resposta.

Logs sem conteúdo sensível:

```bash
docker compose logs --tail=100 app evolution
```

O serviço não registra transcrição nem bytes de áudio. Evolution recebe `DATABASE_SAVE_DATA_NEW_MESSAGE=false` e não persiste mensagens/chats/contatos históricos do app; a instância e os dados de sessão permanecem no volume `evolution_instances` para manter o login.

## Desenvolvimento e testes

```bash
uv sync --all-groups
uv run pytest -q
uv run ruff check .
```

Os testes são locais, não usam número real, OpenAI nem rede externa. Contrato verificado contra a tag `2.3.7` do repositório oficial:

- Criar webhook: `POST /webhook/set/{instance}`; campos `enabled`, `url`, `headers`, `byEvents`, `events`.
- Obter mídia da mensagem: `POST /chat/getBase64FromMediaMessage/{instance}`, body `{ "message": <objeto data do evento> }`.
- Enviar texto: `POST /message/sendText/{instance}`, body `{ "number": "...", "text": "..." }`.
- Evento: `MESSAGES_UPSERT` (payload com `instance`, `data.key`, `data.message.audioMessage`).

Referências: [código Evolution API 2.3.7](https://github.com/evolution-foundation/evolution-api/tree/2.3.7) e [tag Docker publicada pelo workflow do projeto](https://github.com/evolution-foundation/evolution-api/blob/2.3.7/.github/workflows/publish_docker_image.yml).

## Privacidade e limpeza

O backend mantém apenas ID/status/horário da mensagem para idempotência em `app_data`; não guarda o áudio ou a transcrição. O processamento do áudio é local com `faster-whisper`; o modelo é baixado do Hugging Face na primeira inicialização, mas os bytes do áudio não são enviados a um serviço de transcrição externo. A Evolution API continua recebendo os dados da mensagem no fluxo local. Para remover a sessão e todos os dados locais, pare os serviços e remova os volumes **(isso desconecta o WhatsApp e apaga o estado)**:

```bash
docker compose down -v
```

A chamada Whisper transmite o áudio à OpenAI para transcrição; consulte as políticas de retenção do provedor antes de usar conteúdo sensível.
