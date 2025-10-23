import json
import requests
import datetime as dt
import os
from dotenv import load_dotenv

# -----------------------------
# 🌱 .env 로드
# -----------------------------
load_dotenv()

API_KEY = os.getenv("RIOT_API_KEY")
if not API_KEY:
    print("❌ .env 파일에서 RIOT_API_KEY를 불러올 수 없습니다.")
    exit()

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Riot-Token": API_KEY
}

# -----------------------------
# 🔹 절대 경로 설정
# -----------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "ko_kr.json")

if not os.path.exists(DATA_PATH):
    print(f"❌ {DATA_PATH} 파일을 찾을 수 없습니다.")
    exit()

with open(DATA_PATH, "r", encoding="utf-8") as f:
    cdragon_data = json.load(f)

# -----------------------------
# 🔹 한글 이름 매핑 (완전 통일)
# -----------------------------
champ_translation = {}
trait_translation = {}
item_translation = {}
augment_translation = {}

for set_block in cdragon_data.get("setData", []):
    # 챔피언 이름
    for champ in set_block.get("champions", []):
        api_name = champ.get("apiName", "").lower().replace("tft_", "").replace("tft15_", "")
        champ_translation[api_name] = champ.get("name", api_name)

    # 특성(시너지)
    for trait in set_block.get("traits", []):
        api_name = trait.get("apiName", "").lower().replace("tft_", "").replace("tft15_", "")
        trait_translation[api_name] = trait.get("name", api_name)

# 아이템 이름
for item in cdragon_data.get("items", []):
    name = item.get("name", "")
    api_name = item.get("apiName", "")
    if api_name:
        item_translation[api_name.lower().replace("tft_", "").replace("tft15_", "")] = name

# 증강체
for augment in cdragon_data.get("augments", []):
    api_name = augment.get("apiName", "").lower().replace("tft_", "").replace("tft15_", "")
    augment_translation[api_name] = augment.get("name", api_name)

# -----------------------------
# 공통 함수
# -----------------------------
def get_r(url):
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r
    print(f"❌ 상태코드 {r.status_code}: {url}")
    return None


def get_puuid_by_riotid(name, tag):
    url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{name}/{tag}"
    r = get_r(url)
    return r.json().get("puuid") if r else None


def get_recent_match_id(puuid, count=5):
    url = f"https://asia.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids?count={count}"
    r = get_r(url)
    return r.json() if r else []


def get_match_detail(match_id):
    url = f"https://asia.api.riotgames.com/tft/match/v1/matches/{match_id}"
    r = get_r(url)
    return r.json() if r else None


def format_time(epoch_ms):
    return dt.datetime.fromtimestamp(epoch_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")

# -----------------------------
# 콘솔 출력용
# -----------------------------
def print_match_summary(player_info, match_data, index):
    print(f"\n🎮 [최근 경기 {index+1}] ------------------------------")
    print(f"등수: {player_info['placement']} | 레벨: {player_info['level']} | 피해량: {player_info['total_damage_to_players']} | 남은 골드: {player_info['gold_left']}")
    print(f"게임 시간: {format_time(match_data['info']['game_datetime'])}")
    print("-" * 60)

    # 시너지
    print("🔥 시너지:")
    for t in sorted(player_info.get("traits", []), key=lambda x: x["num_units"], reverse=True):
        if t["num_units"] > 0:
            key = t["name"].lower().replace("tft_", "").replace("tft15_", "")
            kor = trait_translation.get(key, key)
            print(f"- {kor} ({t['num_units']}명)")

    print("-" * 60)
    print("🧙 유닛 구성:")
    for u in player_info.get("units", []):
        key = u["character_id"].lower().replace("tft_", "").replace("tft15_", "")
        name = champ_translation.get(key, key)
        print(f"- {name} (⭐{u['tier']})")

    if player_info.get("augments"):
        print("-" * 60)
        print("🧩 증강체:")
        for a in player_info["augments"]:
            key = a.lower().replace("tft_", "").replace("tft15_", "")
            kor = augment_translation.get(key, key)
            print(f"- {kor}")

# -----------------------------
# 챗봇용 (HTML 리턴)
# -----------------------------
def get_match_summary_by_name(riot_id: str) -> str:
    try:
        if "#" not in riot_id:
            return "❌ 소환사명을 정확히 입력해주세요. 예: Hide on bush#KR1"

        name, tag = riot_id.split("#")
        puuid = get_puuid_by_riotid(name, tag)
        if not puuid:
            return f"❌ '{riot_id}' 유저를 찾을 수 없습니다."

        match_ids = get_recent_match_id(puuid, count=3)
        if not match_ids:
            return "⚠️ 최근 전적이 없습니다."

        result = f"🔎 [{riot_id}]님의 최근 경기 정보입니다.<br><br>"

        for i, match_id in enumerate(match_ids):
            match_data = get_match_detail(match_id)
            if not match_data:
                continue

            player = next((p for p in match_data["info"]["participants"] if p["puuid"] == puuid), None)
            if not player:
                continue

            result += f"<b>🎮 [최근 경기 {i+1}]</b><br>"
            result += f"등수: {player['placement']} | 레벨: {player['level']} | 피해량: {player['total_damage_to_players']} | 남은 골드: {player['gold_left']}<br>"
            result += f"게임 시간: {format_time(match_data['info']['game_datetime'])}<br><br>"

            # 시너지
            result += "<b>🔥 시너지:</b><br>"
            for t in sorted(player.get("traits", []), key=lambda x: x["num_units"], reverse=True):
                if t["num_units"] > 0:
                    key = t["name"].lower().replace("tft_", "").replace("tft15_", "")
                    kor = trait_translation.get(key, key)
                    result += f"- {kor} ({t['num_units']}명)<br>"

            # 유닛
            result += "<br><b>🧙 유닛 구성:</b><br>"
            for u in player.get("units", []):
                key = u["character_id"].lower().replace("tft_", "").replace("tft15_", "")
                kor = champ_translation.get(key, key)
                result += f"- {kor} (⭐{u['tier']})<br>"

            # 증강체
            if player.get("augments"):
                result += "<br><b>🧩 증강체:</b><br>"
                for a in player["augments"]:
                    key = a.lower().replace("tft_", "").replace("tft15_", "")
                    kor = augment_translation.get(key, key)
                    result += f"- {kor}<br>"

            result += "<hr>"

        return result

    except Exception as e:
        return f"⚠️ 오류 발생: {e}"
