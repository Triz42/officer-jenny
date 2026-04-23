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
**Windows:** Baixe em https://python.org (versão 3.10 ou superior).

**Linux (Debian/Ubuntu/DigitalOcean):** O Python já vem instalado. Garanta que o pacote completo está disponível:
```bash
sudo apt install python3-full python3-venv -y
```

### 2. Crie e ative um ambiente virtual

> ⚠️ Em sistemas Linux modernos (Debian 12+, Ubuntu 23+), o `pip` não pode instalar
> pacotes diretamente no sistema. Use um ambiente virtual.

**Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

O terminal vai mostrar `(venv)` no início da linha quando o ambiente estiver ativo.

### 3. Instale as dependências

Com o ambiente virtual ativo, rode:
```bash
pip install -r requirements.txt
```

### 4. Configure o `.env`
Edite o arquivo `.env` e coloque a URL do seu webhook do Discord:
```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/SEU_ID/SEU_TOKEN
PORT=8080
```

> ⚠️ Crie um **novo** webhook no Discord para o bot usar.
> Não use o mesmo webhook que está no `webhooks.json` do mod!

### 5. Configure o mod
No `webhooks.json` do Cobblemon Spawn Alerts, mude o `webhookURL` para apontar pro bot:
```json
"webhookURL": "http://localhost:8080/webhook"
```

O bot recebe o payload, busca os dados na PokeAPI e encaminha enriquecido ao Discord.

### 6. Rode o bot

**Importante:** o ambiente virtual precisa estar ativo toda vez que for rodar o bot.

```bash
source venv/bin/activate   # Linux (pule se já estiver ativo)
python bot.py
```

Você vai ver:
```
[BOT] Rodando na porta 8080...
[BOT] Aponte o webhookURL do mod para: http://localhost:8080/webhook
```

#### Rodando em background no droplet (opcional)

Para manter o bot rodando mesmo após fechar o terminal SSH:
```bash
nohup python bot.py &> bot.log &
```

Para parar:
```bash
pkill -f bot.py
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

- O PC/servidor onde o bot roda precisa estar ligado enquanto o servidor Minecraft estiver rodando
- A porta 8080 precisa estar acessível pelo servidor Minecraft
  - Se o servidor Minecraft também está no mesmo PC/droplet: use `localhost`
  - Se o servidor está em outra máquina na rede: use o IP local do PC
  - Se o servidor está em VPS remota: libere a porta no firewall (`sudo ufw allow 8080`)