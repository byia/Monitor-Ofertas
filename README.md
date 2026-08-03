# ML Watcher — monitoramento automático de preços do Mercado Livre

Manda um link de anúncio pro bot no Telegram. Ele registra e passa a
monitorar sozinho, verificando o preço periodicamente e te avisando
**automaticamente** quando cair de verdade — sem você precisar reenviar o
link.

## Estrutura

```
main.py                       → junta tudo e sobe o bot
config.py                     → variáveis de ambiente
database/db.py                → conexão e schema do SQLite
database/repository.py        → salvar/buscar (sem regra de negócio)
providers/mercadolivre.py      → tudo específico do Mercado Livre
services/monitoring_service.py→ regra de negócio (quando alertar, como formatar)
bot/handlers.py                → só conversa com o Telegram
```

Se um dia quiser adicionar outra loja (Amazon, Magalu...), cria um novo
arquivo em `providers/` seguindo a mesma interface (`extrair_item_id` e
`consultar`) — o resto do sistema não precisa mudar.

## 1. Configurar

Copie `.env.example` para `.env` (ou defina as variáveis direto no ambiente)
e preencha:

- `TELEGRAM_TOKEN`: o token do BotFather
- `ALLOWED_USER_IDS`: seu `chat_id` do Telegram, pra só você poder usar o bot
  (pegue mandando uma mensagem pro **@userinfobot**). Deixe vazio se quiser
  que qualquer pessoa possa usar.
- `CHECK_INTERVAL_HOURS`: de quanto em quanto tempo verifica os preços (padrão: 6h)
- `MIN_ALERT_PERCENT`: queda mínima em relação ao último preço visto pra
  disparar alerta (padrão: 10%)

## 2. Rodar localmente

```bash
pip install -r requirements.txt

# Linux/Mac
export TELEGRAM_TOKEN="seu_token"
export ALLOWED_USER_IDS="seu_chat_id"

# Windows PowerShell
$env:TELEGRAM_TOKEN="seu_token"
$env:ALLOWED_USER_IDS="seu_chat_id"

python main.py
```

Se aparecer "Bot rodando" no terminal, funcionou. Manda um link de anúncio
pro bot no Telegram pra testar.

## 3. Deixar rodando 24h (Railway)

1. Suba essa pasta inteira num repositório do GitHub
2. Crie conta em https://railway.app (tem plano gratuito com limite de horas/mês)
3. "New Project" → "Deploy from GitHub repo"
4. Em "Variables", adicione `TELEGRAM_TOKEN`, `ALLOWED_USER_IDS`,
   `CHECK_INTERVAL_HOURS`, `MIN_ALERT_PERCENT`
5. Em "Settings" → "Start Command": `python main.py`

**Sobre o banco:** o SQLite fica no disco do serviço. Dependendo do plano do
Railway, o disco pode resetar em cada novo deploy. Se isso acontecer, é uma
troca pontual em `database/db.py` pra apontar pra um Postgres (o Railway
também oferece Postgres gratuito) — o resto do código não muda, porque o
`repository.py` é a única camada que conhece o banco.

## Como o alerta funciona

- O bot **nunca** confia no "de/por" que a própria loja mostra
- Ele compara o preço atual com o **histórico que ele mesmo observou** (mínimo, média, e principalmente o último preço visto)
- Só notifica quando: bate um novo mínimo histórico, OU cai `MIN_ALERT_PERCENT`%
  ou mais desde a última verificação
- Se o preço subir ou ficar estável, ele não te incomoda de novo
