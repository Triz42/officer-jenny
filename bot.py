import os
import re
import asyncio
import aiohttp
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8080))
try:
    PLAYERS_MAP: dict = json.loads(os.getenv("PLAYERS_MAP", "{}"))
except json.JSONDecodeError:
    print("[WARN] PLAYERS_MAP no .env tem formato inválido. Usando mapa vazio.")
    PLAYERS_MAP = {}
GITLAB_BASE = (
    "https://gitlab.com/cable-mc/cobblemon/-/raw/main"
    "/common/src/main/resources/data/cobblemon/species"
)

GENERATION_MAP = {
    "generation-i":    "generation1",
    "generation-ii":   "generation2",
    "generation-iii":  "generation3",
    "generation-iv":   "generation4",
    "generation-v":    "generation5",
    "generation-vi":   "generation6",
    "generation-vii":  "generation7",
    "generation-viii": "generation8",
    "generation-ix":   "generation9",
}

TYPE_COLORS = {
    "normal":   10329495,
    "fire":     16737792,
    "water":    6594239,
    "electric": 16306224,
    "grass":    7915600,
    "ice":      9830655,
    "fighting": 12595200,
    "poison":   10502304,
    "ground":   14729344,
    "flying":   11047679,
    "psychic":  16711799,
    "bug":      11057664,
    "rock":     12099888,
    "ghost":    7364781,
    "dragon":   7077855,
    "dark":     7362632,
    "steel":    12105936,
    "fairy":    16316671,
}

TYPE_EMOJI = {
    "normal":   "⬜",
    "fire":     "🔥",
    "water":    "💧",
    "electric": "⚡",
    "grass":    "🌿",
    "ice":      "❄️",
    "fighting": "🥊",
    "poison":   "☠️",
    "ground":   "🌍",
    "flying":   "🌪️",
    "psychic":  "🔮",
    "bug":      "🐛",
    "rock":     "🪨",
    "ghost":    "👻",
    "dragon":   "🐉",
    "dark":     "🌑",
    "steel":    "⚙️",
    "fairy":    "✨",
}

# Emojis para os tipos de trigger de evolução
EVO_TRIGGER_EMOJI = {
    "level-up":       "⬆️",
    "use-item":       "🪨",
    "trade":          "🔄",
    "shed":           "🐚",
    "spin":           "🌀",
    "tower-of-darkness": "🏯",
    "tower-of-waters":   "🏯",
    "three-critical-hits": "⚔️",
    "take-damage":    "💥",
    "other":          "❓",
    "agile-style-move": "💨",
    "strong-style-move": "💪",
    "recoil-damage":  "💢",
}


def fmt_item(item_id: str) -> str:
    """Formata item ID: 'cobblemon:oran_berry' → 'Oran Berry'."""
    name = item_id.split(":")[-1]
    return name.replace("_", " ").title()


def fmt_move(move_id: str) -> str:
    """Formata move ID: 'cobblemon:tackle' → 'Tackle'."""
    name = move_id.split(":")[-1]
    return name.replace("_", " ").title()

def format_coordinates(description: str) -> str:
    """Reformata coordenadas na descrição de '(-4864, 95, -3081)' para 'X: -4864 | Y: 95 | Z: -3081'."""
    def replacer(match):
        x, y, z = match.group(1), match.group(2), match.group(3)
        return f"X: {x} | Y: {y} | Z: {z}"
 
    return re.sub(r"\((-?\d+),\s*(-?\d+),\s*(-?\d+)\)", replacer, description)

async def fetch_pokeapi_data(dex_number: int, session: aiohttp.ClientSession) -> dict:
    """Busca dados gerais, espécie e cadeia de evolução na PokeAPI."""
    headers = {"User-Agent": "cobblemon-discord-bot/1.0"}
    pokemon, species, evo_chain = {}, {}, {}

    async with session.get(
        f"https://pokeapi.co/api/v2/pokemon/{dex_number}", headers=headers
    ) as resp:
        if resp.status == 200:
            pokemon = await resp.json(content_type=None)

    async with session.get(
        f"https://pokeapi.co/api/v2/pokemon-species/{dex_number}", headers=headers
    ) as resp:
        if resp.status == 200:
            species = await resp.json(content_type=None)

    evo_url = species.get("evolution_chain", {}).get("url")
    if evo_url:
        async with session.get(evo_url, headers=headers) as resp:
            if resp.status == 200:
                evo_chain = await resp.json(content_type=None)

    return {"pokemon": pokemon, "species": species, "evo_chain": evo_chain}


async def fetch_cobblemon_species(
    pokemon_name: str,
    generation_key: str,
    session: aiohttp.ClientSession,
) -> dict:
    """Busca o JSON de espécie do repositório do Cobblemon no GitLab."""
    gen_folder = GENERATION_MAP.get(generation_key)
    if not gen_folder:
        print(f"[WARN] Geração desconhecida: {generation_key}")
        return {}

    url = f"{GITLAB_BASE}/{gen_folder}/{pokemon_name.lower()}.json"
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json(content_type=None)
                print(f"[OK] Species do Cobblemon carregado: {pokemon_name}")
                return data
            print(f"[WARN] Cobblemon species não encontrado ({resp.status}): {url}")
    except Exception as e:
        print(f"[WARN] Erro ao buscar species do Cobblemon: {e}")
    return {}


def parse_drops(cobblemon_data: dict) -> str:
    drops = cobblemon_data.get("drops", {})
    entries = drops.get("entries", [])
    if not entries:
        return "Nenhum drop registrado."

    lines = []
    for entry in entries:
        item = fmt_item(entry.get("item", "?"))
        pct = entry.get("percentage", 100)

        qty_range = entry.get("quantityRange")

        # quantityRange pode ser string "1-3", dict {"min":1,"max":3}, ou ausente
        if isinstance(qty_range, str) and "-" in qty_range:
            parts = qty_range.split("-")
            qty_min, qty_max = int(parts[0]), int(parts[1])
        elif isinstance(qty_range, dict):
            qty_min = qty_range.get("min", entry.get("quantity", 1))
            qty_max = qty_range.get("max", qty_min)
        else:
            qty_min = qty_max = entry.get("quantity", 1)

        qty_str = f"x{qty_min}" if qty_min == qty_max else f"x{qty_min}–{qty_max}"
        lines.append(f"• {item} {qty_str} ({pct}%)")

    return "\n".join(lines)


def parse_moveset(cobblemon_data: dict, max_moves: int = 10) -> str:
    """Extrai os primeiros moves level-up do learnset do Cobblemon.
    
    Suporta dois formatos:
      - String: "1,cobblemon:scratch"
      - Dict:   {"move": "cobblemon:scratch", "methods": [{"type": "level_up", "level": 1}]}
    """
    learnset = cobblemon_data.get("moves", [])
    if not learnset:
        return "Moveset não disponível."

    level_moves = []

    for entry in learnset:
        # Formato string: "7,cobblemon:ember"
        if isinstance(entry, str):
            parts = entry.split(":", 1)
            if len(parts) == 2:
               level_str, move_id = parts
               if level_str.isdigit():
                   level_moves.append((int(level_str), fmt_move(move_id)))

        # Formato dict: {"move": "...", "methods": [...]}
        elif isinstance(entry, dict):
            move_name = fmt_move(entry.get("move", "?"))
            for method in entry.get("methods", []):
                if  method.get("type") == "level_up":
                    level = method.get("level", 0)
                    level_moves.append((level, move_name))
                    break

    if not level_moves:
        return "Moveset não disponível."

    level_moves.sort(key=lambda x: x[0])
    return "\n".join(f"• Lv.{lvl} {move}" for lvl, move in level_moves[:max_moves])

def parse_nature(cobblemon_data: dict) -> str:
    nature = cobblemon_data.get("nature")
    return nature.replace("_", " ").title() if nature else "N/A"

def parse_ability(cobblemon_data: dict) -> str:
    ability = cobblemon_data.get("ability")
    return ability.replace("_", " ").title() if ability else "N/A"

def parse_nearest_player(fields: list) -> str:
    fields_map = {
        f.get("name", "").replace("*", "").strip().lower(): f.get("value", "N/A")
        for f in fields
    }
    nearest = fields_map.get("nearest player", fields_map.get("nearest_player", "N/A"))
    if nearest and nearest != "N/A":
        discord_id = PLAYERS_MAP.get(nearest.strip())
        if discord_id:
            return f"<@{discord_id}>"
        return nearest
    return "N/A"

def get_english_description(species: dict) -> str:
    for entry in species.get("flavor_text_entries", []):
        if entry.get("language", {}).get("name") == "en":
            return entry["flavor_text"].replace("\n", " ").replace("\f", " ")
    return "No description available."


def _format_evolution_details(details: dict) -> list[str]:
    """
    Recebe um dict de 'evolution_details' da PokeAPI e retorna
    uma lista de strings descrevendo cada requisito.
    """
    reqs = []

    trigger = details.get("trigger", {}).get("name", "other")
    emoji   = EVO_TRIGGER_EMOJI.get(trigger, "❓")

    # Trigger principal
    trigger_label = trigger.replace("-", " ").title()
    reqs.append(f"{emoji} **{trigger_label}**")

    # Nível mínimo
    min_level = details.get("min_level")
    if min_level:
        reqs.append(f"⬆️ Nível mínimo: **{min_level}**")

    # Item usado (ex: Thunder Stone)
    item = details.get("item")
    if item:
        item_name = item.get("name", "?").replace("-", " ").title()
        reqs.append(f"🪨 Item: **{item_name}**")

    # Item segurado (held item)
    held_item = details.get("held_item")
    if held_item:
        held_name = held_item.get("name", "?").replace("-", " ").title()
        reqs.append(f"🎒 Held Item: **{held_name}**")

    # Felicidade mínima
    min_happiness = details.get("min_happiness")
    if min_happiness:
        reqs.append(f"💛 Felicidade mínima: **{min_happiness}**")

    # Beleza mínima (gen III contests)
    min_beauty = details.get("min_beauty")
    if min_beauty:
        reqs.append(f"💄 Beleza mínima: **{min_beauty}**")

    # Afinidade mínima
    min_affection = details.get("min_affection")
    if min_affection:
        reqs.append(f"💖 Afinidade mínima: **{min_affection}**")

    # Move conhecido
    known_move = details.get("known_move")
    if known_move:
        move_name = known_move.get("name", "?").replace("-", " ").title()
        reqs.append(f"📖 Saber o move: **{move_name}**")

    # Tipo de move conhecido
    known_move_type = details.get("known_move_type")
    if known_move_type:
        type_name = known_move_type.get("name", "?").capitalize()
        reqs.append(f"🏷️ Saber move do tipo: **{type_name}**")

    # Localização
    location = details.get("location")
    if location:
        loc_name = location.get("name", "?").replace("-", " ").title()
        reqs.append(f"📍 Local: **{loc_name}**")

    # Precisar de chuva
    needs_rain = details.get("needs_overworld_rain")
    if needs_rain:
        reqs.append("🌧️ Requer: **Chuva no mundo**")

    # Turno do dia
    time_of_day = details.get("time_of_day")
    if time_of_day:
        time_map = {"day": "☀️ Dia", "night": "🌙 Noite", "dusk": "🌆 Entardecer"}
        reqs.append(f"🕐 Horário: **{time_map.get(time_of_day, time_of_day.title())}**")

    # Gênero específico
    gender = details.get("gender")
    if gender is not None:
        gender_label = "♂️ Macho" if gender == 1 else "♀️ Fêmea"
        reqs.append(f"🔬 Gênero: **{gender_label}**")

    # Pokémon na party
    party_species = details.get("party_species")
    if party_species:
        party_name = party_species.get("name", "?").capitalize()
        reqs.append(f"👥 Ter na party: **{party_name}**")

    # Tipo de Pokémon na party
    party_type = details.get("party_type")
    if party_type:
        ptype = party_type.get("name", "?").capitalize()
        reqs.append(f"👥 Party com tipo: **{ptype}**")

    # Trade species (troca específica)
    trade_species = details.get("trade_species")
    if trade_species:
        trade_name = trade_species.get("name", "?").capitalize()
        reqs.append(f"🔄 Trocar com: **{trade_name}**")

    # Virar de cabeça para baixo (Inkay)
    turn_upside_down = details.get("turn_upside_down")
    if turn_upside_down:
        reqs.append("🙃 Virar o dispositivo de cabeça para baixo")

    return reqs


def parse_evolution_requirements(chain: dict) -> str:
    """
    Percorre a cadeia de evolução da PokeAPI e monta uma string
    formatada com nome de cada estágio e seus requisitos.

    Exemplo de saída:
        🌱 **Bulbasaur**
        ↓ ⬆️ Level-Up · ⬆️ Nível mínimo: **16**
        🌿 **Ivysaur**
        ↓ ⬆️ Level-Up · ⬆️ Nível mínimo: **32**
        🌺 **Venusaur**
    """
    if not chain:
        return "Sem dados de evolução."

    lines = []

    def traverse(node, depth=0):
        species_name = node.get("species", {}).get("name", "?").capitalize()

        # Primeiro estágio não tem detalhes de evolução
        if depth == 0:
            lines.append(f"🥚 **{species_name}**")
        else:
            lines.append(f"{'→ ' * depth}✨ **{species_name}**")

        for evo_node in node.get("evolves_to", []):
            evo_details_list = evo_node.get("evolution_details", [])
            evo_name = evo_node.get("species", {}).get("name", "?").capitalize()

            if evo_details_list:
                for evo_details in evo_details_list:
                    reqs = _format_evolution_details(evo_details)
                    # Agrupa os requisitos em uma linha separada por " · "
                    reqs_str = " · ".join(reqs)
                    lines.append(f"{'  ' * (depth + 1)}↳ {reqs_str}")

            traverse(evo_node, depth + 1)

    traverse(chain.get("chain", {}))

    if not lines:
        return "Sem dados de evolução."

    return "\n".join(lines)


def get_embed_color(types: list, is_shiny: bool) -> int:
    if is_shiny:
        return 16766720  # Dourado
    if types:
        return TYPE_COLORS.get(types[0], 10329495)
    return 10329495


async def send_enriched_webhook(payload: dict):
    """Monta e envia o embed enriquecido para o Discord."""
    dex_number = None
    embeds = payload.get("embeds", [])
    pokemon_name_raw = "unknown"
    is_shiny = False

    if embeds:
        description = format_coordinates(embeds[0].get("description", ""))
        title = embeds[0].get("title", "")
        fields = embeds[0].get("fields", [])
        is_shiny = "shiny" in title.lower()

        # Nome do Pokémon vindo do title
        skip = {"a", "an", "shiny", "legendary", "mythical", "ultrabeast",
                "paradox", "spawned", "in", "biome!", "the", "ultra", "rare",
                "common", "uncommon", ""}
        for part in title.replace("*", "").replace("✨", "").split():
            if part.lower() not in skip:
                pokemon_name_raw = part.lower()
                break

        # Dex number vindo dos fields
        for field in fields:
            if field.get("name", "").lower() == "dex":
                match = re.search(r"(\d+)", field.get("value", ""))
                if match:
                    dex_number = int(match.group(1))
                    break

    if not dex_number:
        print("[WARN] Dex number não encontrado. Encaminhando payload original.")
        async with aiohttp.ClientSession() as session:
            await session.post(DISCORD_WEBHOOK_URL, json=payload)
        return

        

    async with aiohttp.ClientSession() as session:
        pokeapi_data = await fetch_pokeapi_data(dex_number, session)

        pokemon      = pokeapi_data.get("pokemon", {})
        species      = pokeapi_data.get("species", {})
        evo_data     = pokeapi_data.get("evo_chain", {})
        generation_key = species.get("generation", {}).get("name", "")

        cobblemon_data = await fetch_cobblemon_species(
            pokemon_name_raw, generation_key, session
        )

    # PokeAPI
    types = [t["type"]["name"] for t in pokemon.get("types", [])]
    types_display = " / ".join(
        f"{TYPE_EMOJI.get(t, '')} {t.capitalize()}" for t in types
    )

    capture_rate = species.get("capture_rate", "?")
    capture_pct  = round((capture_rate / 255) * 100, 1) if isinstance(capture_rate, int) else "?"
    pokedex_desc = get_english_description(species)

    # ─── EVOLUÇÃO COM REQUISITOS DETALHADOS ───────────────────────────────────
    evo_display = parse_evolution_requirements(evo_data) if evo_data else "Sem dados de evolução."

    # Cobblemon GitLab
    drops_display   = parse_drops(cobblemon_data)
    moveset_display = parse_moveset(cobblemon_data)
    nature_display = parse_nature(cobblemon_data)
    ability_display = parse_ability(cobblemon_data)
    nearest_player_display = parse_nearest_player(fields)

    color = get_embed_color(types, is_shiny)
    artwork_url = (
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master"
        f"/sprites/pokemon/other/official-artwork/{dex_number}.png"
    )

    original_embed = embeds[0] if embeds else {}

    enriched_embed = {
        "title":       original_embed.get("title", f"A {pokemon_name_raw.capitalize()} spawned!"),
        "description": original_embed.get("description", ""),
        "color":       color,
        "thumbnail":   {"url": artwork_url},
        "fields": [
            {
                "name":   "📖 Pokédex",
                "value":  pokedex_desc,
                "inline": False,
            },
            {
                "name":   "🏷️ Tipo",
                "value":  types_display,
                "inline": True,
            },
            {
                "name":   "⚾ Catch Rate",
                "value":  f"{capture_rate}/255 ({capture_pct}%)",
                "inline": True,
            },
            {
                "name":   "🔁 Linha Evolutiva",
                "value":  evo_display,
                "inline": False,
            },
            {
                "name":   "⚔️ Moveset (Level-up)",
                "value":  moveset_display,
                "inline": True,
            },
            {
                "name":   "💰 Drops",
                "value":  drops_display,
                "inline": True,
            },
            {
                "name":   "🌿 Natureza",
                "value":  nature_display,
                "inline": True,
            },
            {
                "name":   "✴️ Habilidade",
                "value":  ability_display,
                "inline": True,
            },
            {
                "name":   "👤 Jogador mais próximo",
                "value":  nearest_player_display,
                "inline": False,
            },
        ],
        "footer":    original_embed.get("footer", {}),
        "timestamp": original_embed.get("timestamp"),
    }

    enriched_payload = {
        "content":    payload.get("content", ""),
        "username":   payload.get("username", "Cobblemon Alerts"),
        "avatar_url": payload.get("avatar_url", ""),
        "embeds":     [enriched_embed],
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(DISCORD_WEBHOOK_URL, json=enriched_payload) as resp:
            if resp.status not in (200, 204):
                print(f"[ERRO] Discord retornou {resp.status}: {await resp.text()}")
            else:
                print(f"[OK] {pokemon_name_raw.capitalize()} (#{dex_number}) enviado.")


@app.route("/webhook", methods=["POST"])
def receive_webhook():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "Payload inválido"}), 400

    print("[DEBUG] Payload recebido:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    asyncio.run(send_enriched_webhook(payload))
    return jsonify({"status": "ok"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "running"}), 200


if __name__ == "__main__":
    print(f"[BOT] Rodando na porta {PORT}...")
    app.run(host="0.0.0.0", port=PORT)