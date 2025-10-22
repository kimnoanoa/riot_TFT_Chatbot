import json
import pandas as pd
import re
import os

# --- 1. 파일 경로 정의 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)  # web 기준 상위 폴더 (RIOT_TFT)

CHAMPION_FILE_PATH = os.path.join(ROOT_DIR, "data", "champion_data.json")
CHALLENGER_FILE_PATH = os.path.join(ROOT_DIR, "data", "20251014_tft_all_tiers_10each.csv")


# --- 2. 데이터 로드 및 전처리 ---
def load_data():
    """CSV / JSON 데이터를 로드하고 키워드 맵을 생성"""
    # 챔피언 데이터
    try:
        with open(CHAMPION_FILE_PATH, 'r', encoding='utf-8') as f:
            champion_data = json.load(f)
        print(f"✅ {len(champion_data)}개의 챔피언 데이터 로드 완료!")
    except Exception as e:
        print(f"❌ 챔피언 데이터 로드 실패: {e}")
        champion_data = {}

    # 챌린저 CSV
    try:
        df = pd.read_csv(CHALLENGER_FILE_PATH)
        challenger_data = df.to_dict(orient="records")
        print(f"✅ 챌린저 CSV {len(challenger_data)}개 로드 완료!")
    except Exception as e:
        print(f"⚠️ 챌린저 CSV 로드 실패: {e}")
        challenger_data = []

    # 챔피언 키워드 맵 생성
    keyword_map = {}
    for kor_name, data in champion_data.items():
        keyword_map[kor_name.lower()] = kor_name
        for kw in data.get("keywords", []):
            keyword_map[kw.lower()] = kor_name

    return challenger_data, champion_data, keyword_map


CHALLENGER_DATA_GLOBAL, CHAMPION_DATA_GLOBAL, KEYWORD_TO_NAME_MAP = load_data()


# --- 3. 챔피언 이름 추출 ---
def extract_champion_from_query(query):
    query = query.lower()
    found = []
    for key in sorted(KEYWORD_TO_NAME_MAP.keys(), key=len, reverse=True):
        kor_name = KEYWORD_TO_NAME_MAP[key]
        if key in query and kor_name not in found:
            found.append(kor_name)
            query = query.replace(key, " " * len(key))
    return found


# --- 4. 시너지 / 덱 헬퍼 ---

# ✅ 시너지명 정규화 함수 추가
def normalize_synergy(name):
    if not isinstance(name, str):
        return ""
    return name.strip().lower()


def get_champion_synergies(champ):
    champ = champ.strip()  # 공백 제거
    data = CHAMPION_DATA_GLOBAL.get(champ) or CHAMPION_DATA_GLOBAL.get(champ.strip()) or {}

    
    s = set()

    # ✅ 최상위 synergy 필드 포함
    if isinstance(data.get("synergy"), list):
        s.update(normalize_synergy(x) for x in data["synergy"])

    # ✅ deck 내부 synergy 포함
    for d in data.get("deck", []):
        if isinstance(d.get("synergy"), list):
            s.update(normalize_synergy(x) for x in d["synergy"])
    return sorted(list(s))

    


def find_common_synergies(champs):
    """여러 챔피언 간 공통 시너지 교집합"""
    
    if not champs:
        return []

    # ✅ 첫 챔피언 기준으로 시작
    base = set(get_champion_synergies(champs[0]))
    print("🔎", champs[0], "시너지:", get_champion_synergies(champs[0]))
    print("🔎", champs[1], "시너지:", get_champion_synergies(champs[1]))

    # ✅ 이후 챔피언들과 교집합 갱신
    for c in champs[1:]:
        base &= set(get_champion_synergies(c))

    return list(base)





def find_decks_for_multiple_champs(champs):
    matched = []
    for _, data in CHAMPION_DATA_GLOBAL.items():
        for d in data.get("deck", []):
            core = d.get("core", [])
            if all(c in core for c in champs):
                matched.append({
                    "core": core,
                    "synergy": d.get("synergy", []),
                    "comment": d.get("comment", "")
                })
    return matched


def extract_synergies_from_description(desc):
    if not desc:
        return "정보 없음"
    match = re.search(r"은 (.*?) 시너지를 가진", desc)
    return match.group(1).strip() if match else "정보 없음"


# --- 5. 덱 추천 로직 ---
def _recommend_core_deck(champs):
    if len(champs) == 1:
        champ = champs[0]
        data = CHAMPION_DATA_GLOBAL.get(champ)
        if not data or "deck" not in data:
            return f"'{champ}' 챔피언에 대한 덱 정보를 찾을 수 없습니다."

        deck = data["deck"][0]
        synergy = extract_synergies_from_description(data.get("description", ""))
        items = ", ".join(data.get("items", ["추천 아이템 없음"]))
        core = ", ".join(deck.get("core", []))
        synergies = " + ".join(deck.get("synergy", []))
        comment = deck.get("comment", "설명 없음")

        return (
            f"🌟 **{champ}** 챔피언이 핵심인 덱을 추천합니다!\n"
            f"- 🔹 고유 시너지: {synergy}\n"
            f"- 🧩 추천 아이템: {items}\n"
            f"- ⚙️ 코어 챔피언: {core}\n"
            f"- 💫 주요 시너지: {synergies}\n"
            f"- 💡 팁: {comment}"
        )

    elif len(champs) >= 2:
        selected = ", ".join(champs)
        commons = find_common_synergies(champs)
        decks = find_decks_for_multiple_champs(champs)

        if not commons:
            return f"⚠️ {selected} 조합 분석 결과 : 공통 시너지가 없습니다. 다른 덱을 찾아보세요!"

        main_synergy = commons[0]

        if not decks:
            return (
                f"🎯 {selected} 조합 분석 결과\n"
                f"✅ 공통 시너지: {main_synergy}\n"
                f"❌ 매칭된 덱 데이터를 찾지 못했습니다."
            )

        deck = decks[0]
        synergy_str = " + ".join(deck["synergy"])
        core_str = ", ".join(deck["core"])
        comment = deck.get("comment", "설명 없음")

        return (
            f"🎯 {selected} 조합 추천 결과\n"
            f"✅ 공통 시너지: {main_synergy}\n"
            f"✨ 최종 덱 시너지: {synergy_str}\n"
            f"- 🎮 추천 코어 구성: {core_str}\n"
            f"- 💡 팁: {comment}"
        )

    return "챔피언 정보를 찾을 수 없습니다."


# --- 6. Flask 연동용 함수 ---
def process_user_query(user_msg, challenger_data=None):
    champs = extract_champion_from_query(user_msg)
    print("🎯 추출된 챔피언:", champs)

    q_type = "CHAMPION_QUERY" if champs else "UNKNOWN"
    return {
        "query_type": q_type,
        "champions": champs,
        "meta_data": CHALLENGER_DATA_GLOBAL
        
    }
    


def recommend_champion_deck(champs):
    try:
        return _recommend_core_deck(champs)
    except Exception as e:
        print("⚠️ 덱 추천 처리 오류:", e)
        return "추천 결과를 생성하는 중 오류가 발생했습니다."


def recommend_meta_deck(meta_data=None):
    return "메타 분석 기능은 현재 비활성화되어 있습니다. (챔피언 기반 덱 추천만 지원 중)"


# ✅ Flask 호환용 글로벌 변수
CHALLENGER_DATA_GLOBAL = CHALLENGER_DATA_GLOBAL
