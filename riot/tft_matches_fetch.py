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
# 한글 이름 매핑
# -----------------------------
champ_translation = {}
trait_translation = {}
item_translation = {}
augment_translation = {}

for set_block in cdragon_data.get("setData", []):
    for champ in set_block.get("champions", []):
        api_name = champ.get("apiName", "").replace("TFT_", "").replace("TFT15_", "")
        champ_translation[api_name] = champ.get("name", api_name)

    for trait in set_block.get("traits", []):
        api_name = trait.get("apiName", "").replace("TFT_", "").replace("TFT15_", "")
        trait_translation[api_name] = trait.get("name", api_name)

for item in cdragon_data.get("items", []):
    name = item.get("name", "")
    item_id = item.get("id")
    api_name = item.get("apiName", "")
    if item_id is not None:
        item_translation[str(item_id)] = name
    if api_name:
        item_translation[api_name.replace("TFT_", "").replace("TFT15_", "")] = name

for augment in cdragon_data.get("augments", []):
    augment_name = augment.get("apiName", "").replace("TFT_", "").replace("TFT15_", "")
    augment_translation[augment_name] = augment.get("name", augment_name)

# -----------------------------
# API 요청 함수
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
# 매치 요약 (콘솔용)
# -----------------------------
def print_match_summary(player_info, match_data, index):
    print(f"\n\n🎮 [최근 경기 {index+1}] ----------------------------------")
    print(f"등수: {player_info['placement']} | 레벨: {player_info['level']} | 피해량: {player_info['total_damage_to_players']} | 남은 골드: {player_info['gold_left']}")
    print(f"게임 시간: {format_time(match_data['info']['game_datetime'])}")
    print("-" * 60)
    print("📛 시너지(특성):")
    traits = sorted(player_info.get("traits", []), key=lambda x: x["num_units"], reverse=True)
    for t in traits:
        if t["num_units"] > 0:
            trait_key = t["name"].replace("TFT_", "").replace("TFT15_", "")
            kor_trait = trait_translation.get(trait_key, trait_key)
            print(f"- {kor_trait} ({t['num_units']}명)")
    print("-" * 60)
    print("🧙 유닛 구성:")
    for unit in player_info.get("units", []):
        champ_key = unit["character_id"].replace("TFT_", "").replace("TFT15_", "")
        champ_name = champ_translation.get(champ_key, champ_key)
        tier = unit["tier"]
        print(f"- {champ_name} (⭐{tier})")
    augments = player_info.get("augments", [])
    if augments:
        print("-" * 60)
        print("🧩 증강 선택:")
        for aug in augments:
            aug_key = aug.replace("TFT_", "").replace("TFT15_", "")
            kor_aug = augment_translation.get(aug_key, aug)
            print(f"- {kor_aug}")

# -----------------------------
# 메인 실행
# -----------------------------
if __name__ == "__main__":
    riot_id = input("검색할 닉네임 (예: Hide on bush#KR1): ")
    try:
        name, tag = riot_id.split("#")
    except:
        print("❌ 형식이 올바르지 않습니다. 예: Hide on bush#KR1")
        exit()

    puuid = get_puuid_by_riotid(name, tag)
    if not puuid:
        print("❌ 유저를 찾을 수 없습니다.")
        exit()

    match_ids = get_recent_match_id(puuid, count=5)
    if not match_ids:
        print("❌ 최근 경기 정보를 불러올 수 없습니다.")
        exit()

    for i, match_id in enumerate(match_ids):
        match_data = get_match_detail(match_id)
        if not match_data:
            continue
        player_info = next((p for p in match_data["info"]["participants"] if p["puuid"] == puuid), None)
        if player_info:
            print_match_summary(player_info, match_data, i)

# -----------------------------
# 🔹 챗봇용 전적 리턴 함수 (티어 완전 제거)
# -----------------------------
def get_match_summary_by_name(riot_id: str) -> str:
    """
    🔹 챗봇용 전체 전적 리턴 함수 (티어 제거 버전)
    """
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

        result_text = f"🔎 [{riot_id}]님의 최근 경기 상세 정보입니다.<br><br>"

        for i, match_id in enumerate(match_ids):
            match_data = get_match_detail(match_id)
            if not match_data:
                continue
            player_info = next(
                (p for p in match_data["info"]["participants"] if p["puuid"] == puuid),
                None
            )
            if not player_info:
                continue

            # 🎮 경기 요약
            result_text += f"<b>🎮 [최근 경기 {i+1}]</b><br>"
            result_text += (
                f"등수: {player_info['placement']} | "
                f"레벨: {player_info['level']} | "
                f"피해량: {player_info['total_damage_to_players']} | "
                f"남은 골드: {player_info['gold_left']}<br>"
            )
            result_text += f"게임 시간: {format_time(match_data['info']['game_datetime'])}<br><br>"

            # 🔥 시너지(특성)
            result_text += "<b>🔥 시너지(특성):</b><br>"
            traits = sorted(player_info.get("traits", []), key=lambda x: x["num_units"], reverse=True)
            for t in traits:
                if t["num_units"] > 0:
                    t_key = t["name"].replace("TFT_", "").replace("TFT15_", "")
                    t_name = trait_translation.get(t_key, t_key)
                    result_text += f"- {t_name} ({t['num_units']}명)<br>"

            # 🧙 유닛 구성
            result_text += "<br><b>🧙 유닛 구성:</b><br>"
            for unit in player_info.get("units", []):
                u_key = unit["character_id"].replace("TFT_", "").replace("TFT15_", "")
                u_name = champ_translation.get(u_key, u_key)
                tier = unit["tier"]
                result_text += f"- {u_name} (⭐{tier})<br>"

            # 🧩 증강 선택
            augments = player_info.get("augments", [])
            if augments:
                result_text += "<br><b>🧩 증강 선택:</b><br>"
                for aug in augments:
                    a_key = aug.replace("TFT_", "").replace("TFT15_", "")
                    a_name = augment_translation.get(a_key, a_key)
                    result_text += f"- {a_name}<br>"

            result_text += "<hr>"

        return result_text.strip()

    except Exception as e:
        return f"⚠️ 전적 조회 중 오류 발생: {e}"
