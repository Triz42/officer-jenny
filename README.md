# Cobblemon Discord Bot

Bot intermediário que recebe o webhook do mod **Cobblemon Spawn Alerts** e enriquece
a mensagem com dados da PokeAPI antes de enviar ao Discord.

## Dados adicionados automaticamente

- 🏷️ **Tipos** do Pokémon (Fire, Water, etc.) com emoji
- ⚾ **Taxa de captura** (valor e porcentagem)
- 📖 **Descrição da Pokédex** em inglês
- 🔁 **Cadeia de evolução**
- 🎨 **Cor do embed** automática por tipo (dourado para shiny!)

---

## Instalação

### 1. Instale o Python
Baixe em https://python.org (versão 3.10 ou superior).

### 2. Instale as dependências
Abra o terminal na pasta do bot e rode:
```bash
pip install -r requirements.txt
```

### 3. Configure o `.env`
Edite o arquivo `.env` e coloque a URL do seu webhook do Discord:
```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/SEU_ID/SEU_TOKEN
PORT=8080
```

> ⚠️ Crie um **novo** webhook no Discord para o bot usar.
> Não use o mesmo webhook que está no `webhooks.json` do mod!

### 4. Configure o mod
No `webhooks.json` do Cobblemon Spawn Alerts, mude o `webhookURL` para apontar pro bot:
```json
"webhookURL": "http://localhost:8080/webhook"
```

O bot recebe o payload, busca os dados na PokeAPI e encaminha enriquecido ao Discord.

### 5. Rode o bot
```bash
python bot.py
```

Você vai ver:
```
[BOT] Rodando na porta 8080...
[BOT] Aponte o webhookURL do mod para: http://localhost:8080/webhook
```

---

## Como funciona

```
Minecraft (mod) → http://localhost:8080/webhook → bot.py → PokeAPI → Discord
```

1. Um Pokémon spawna no servidor
2. O mod envia o webhook para `http://localhost:8080/webhook`
3. O bot extrai o número da Pokédex do payload
4. Busca tipo, taxa de captura, descrição e evolução na PokeAPI
5. Monta um embed enriquecido e envia ao Discord

---

## Notas

- O PC onde o bot roda precisa estar ligado enquanto o servidor Minecraft estiver rodando
- A porta 8080 precisa estar acessível pelo servidor Minecraft
  - Se o servidor Minecraft também está no mesmo PC: use `localhost`
  - Se o servidor está em outra máquina na rede: use o IP local do PC
  - Se o servidor está em VPS remota: será necessário expor a porta (ngrok ou similar)
