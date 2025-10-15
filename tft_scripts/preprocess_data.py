import json
import os
import pandas as pd

INPUT_PATH = "data/ko_kr.json"  # 파일 이름을 사용자가 업로드한 파일 이름으로 변경했습니다.
OUTPUT_DIR = "data/"

# -------------------------------
# 1) 데이터 로드
# -------------------------------
# NOTE: INPUT_PATH를 'ko_kr (1).json'으로 변경했습니다.
try:
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"⚠️ 에러: 입력 파일 '{INPUT_PATH}'을 찾을 수 없습니다. 경로를 확인해 주세요.")
    exit()

# -------------------------------
# 2) 최신 세트 자동 감지
# -------------------------------
set_list = data.get("setData", [])
if not set_list:
    raise ValueError("⚠️ setData가 비어 있습니다!")

# 가장 큰 number를 가진 세트가 최신 세트입니다.
latest_set = max(set_list, key=lambda s: s.get("number", 0))
set_number = latest_set.get("number")
set_name = latest_set.get("name", "Unknown")

print(f"📦 최신 세트 감지됨 → {set_name} (TFT{set_number})")

# -------------------------------
# 3) 로케일 매핑 (ko_kr 문자열 테이블)
# -------------------------------
locale_map = data.get("localeStrings", {})

def localize_name(raw_name):
    """로케일 키면 한글 실명으로 변환"""
    if not raw_name:
        return raw_name
    return locale_map.get(raw_name, raw_name)

# -------------------------------
# 3-1) 사용자 제공 아이템 이름 목록 (124개)
# -------------------------------
# 사용자가 제공한 124개의 한국어 인게임 아이템 이름 목록입니다.
ALLOWED_ITEM_NAMES = {
    # 재료 아이템
    "B.F. 대검", "곡궁", "쇠사슬 조끼", "음전자 망토", "쓸데없이 큰 지팡이", 
    "여신의 눈물", "거인의 허리띠", "연습용 장갑", "뒤집개", "프라이팬", 

    # 완성 아이템
    "죽음의 검", "거인 학살자", "밤의 끝자락", "피바라기", "마법공학 총검",
    "쇼진의 창", "스테락의 도전", "무한의 대검", "붉은 덩굴정령", "공허의 지팡이",
    "최후의 속삭임", "거인의 결의", "덤불 조끼", "가고일 돌갑옷", "크라운가드",
    "수호자의 맹세", "태양불꽃 망토", "굳건한 심장", "크라켄의 분노", "용의 발톱",
    "적응형 투구", "수은", "구인수의 격노검", "이온 충격기", "라바돈의 죽음모자",
    "대천사의 지팡이", "보석 건틀릿", "푸른 파수꾼", "내셔의 이빨", "저녁갑주", 
    "모렐로노미콘", "정령의 형상", "워모그의 갑옷", "타격대의 철퇴", "정의의 손길", 
    "도적의 장갑", "전략가의 왕관", "전략가의 망토", "전략가의 방패",
   
    # 유물아이템
     "거대한 히드라","거물의 갑옷", "고속 연사포", "끝없는 절망", "도박꾼의 칼날", 
    "리치베인", "마나자네", "마법사의 최후", "망령 해적검", "명멸검", "무한한 삼위일체", 
    "방한 장갑", "불굴", "새벽심장", "생선대가리", "선체분쇄자", "속임수 거울", 
    "수상한 외투", "스태틱의 단검", "승천의 부적", "역병의 보석", "은빛 여명", 
    "자객의 발톱", "저격수의 집중", "존야의 역설", "죽음불꽃 손아귀", "죽음의 저항", 
    "지평선의 초점", "추적자의 팔목 보호대", "활력증진의 펜던트", "황금 징수의 총", 
    "라이트실드 문장"

    # 상징
    "결투가 상징", "마법사 상징", "별 수호자 상징", "봉쇄자 상징",
    "소울 파이터 상징", "수정 갬빗 상징", "슈프림 셀 상징", "신동 상징", "악령 상징", 
    "요새 상징", "이단아 상징", "저격수 상징", "전쟁기계 상징",
    "전투사관학교 상징", "책략가 상징", "처형자 상징", "프로레슬러 상징", "헤비급 상징"
}
# -------------------------------
# 공통 필터 유틸
# -------------------------------
def is_real_champion(cid: str, name: str):
    if not cid.startswith(f"TFT{set_number}_"):
        return False
    banned = [
        "ArmoryKey", "TrainingDummy", "EventPM", "Buddy", "Voidspawn",
        "Crab", "Chest", "Minion", "Golem", "Pet", "PM_", "ElderDragon"
    ]
    if any(b in cid for b in banned): return False
    if any(b in name for b in ["상자", "미니언", "훈련", "테스트", "골렘"]): return False
    return True

def is_real_trait(tid: str, name: str):
    if not tid.startswith(f"TFT{set_number}_"):
        return False
    banned = ["Tutorial", "SetData", "Portal", "Augment", "Mutator", "Test"]
    if any(b in tid for b in banned): return False
    return True

def is_real_item(item: dict):
    """
    챔피언에게 장착 가능한 아이템만 필터링합니다. (최종적으로 ALLOWED_ITEM_NAMES를 사용)
    """
    if not isinstance(item, dict): return False
    api = item.get("apiName", "")
    if not api: return False
    
    # 1. 빠른 필터링 (불필요한 토큰/더미 제거)
    banned_keywords = [
        "Augment", "ArmoryKey", "Consumable", "Tactician", "Stage", "Neeko", 
        "PM_", "Orb", "Dummy", "Test", "Debug", "Unknown", "UnusableSlot", 
        "JammedSlot", "MechanicTrait", "HiddenTech", "MonsterTrainerChoice", 
        "RoboRanger", "CrystalRose_Pass", "SetMechanic_Remover", "DragonFist", 
        "Free", "TraitToken", "Sion_Corpse", "ArmoryItem"
    ]
    if any(b in api for b in banned_keywords): return False
    
    # 2. API Name Prefix Check (현재 세트 전용 또는 공용 TFT_Item_만 허용)
    if not (api.startswith(f"TFT{set_number}_Item_") or api.startswith("TFT_Item_")):
        return False
        
    # 3. 아이템 이름이 없는 경우 (내부 토큰)
    raw_name_key = item.get("name")
    if not raw_name_key: return False

    # 4. 최종적으로 한국어 이름 목록과 일치하는지 확인 (가장 강력한 필터)
    localized_item_name = localize_name(raw_name_key)
    if localized_item_name not in ALLOWED_ITEM_NAMES:
        return False
    
    return True

def is_real_augment(aug: dict):
    """증강만 따로: 현재 세트 또는 공용 증강 접두 허용"""
    if not isinstance(aug, dict):
        return False
    api = aug.get("apiName", "")
    if not api:
        return False
    # ✅ 현재 세트(TFT{set_number}) 접두사 or 공용 증강 접두사만 허용
    if not (api.startswith(f"TFT{set_number}_") or api.startswith("TFT_Augment_")):
        return False
    if any(b in api for b in ["Test", "Tutorial", "Dev", "PM_", "EventPM"]):
        return False
    return True

def normalize_tier(tier_value):
    """증강 티어 표기를 일관화(숫자/문자 혼용 보호)"""
    if tier_value is None:
        return None
    if isinstance(tier_value, str):
        up = tier_value.strip().lower()
        if "silver" in up: return "Silver"
        if "gold" in up: return "Gold"
        if "prismatic" in up or "chromatic" in up: return "Prismatic"
        if up.isdigit():
            return {"1":"Silver","2":"Gold","3":"Prismatic"}.get(up, up)
        return up
    if isinstance(tier_value, (int, float)):
        return {1:"Silver", 2:"Gold", 3:"Prismatic"}.get(int(tier_value), tier_value)
    return tier_value

# -------------------------------
# 4) 챔피언
# -------------------------------
champions = []
for champ in latest_set.get("champions", []):
    cid = champ.get("apiName", "")
    cname = localize_name(champ.get("name", ""))
    if not is_real_champion(cid, cname):
        continue
    
    # 시너지/소환 스킬로 생성된 챔피언 추가 예외처리 (API 이름으로 필터링하는 것이 더 정확함)
    if "치명적인 가시" in cname or "휘감는 뿌리" in cname or "거대 메크 로봇" in cname:
        continue

    ability_name = localize_name(champ.get("ability", {}).get("name", ""))
    ability_desc = champ.get("ability", {}).get("desc", "")

    champions.append({
        "id": cid,
        "name": cname,
        "cost": champ.get("cost"),
        "traits": champ.get("traits", []),
        "ability": {"name": ability_name, "desc": ability_desc},
    })


# -------------------------------
# 5) 특성 (시너지/파워 분리)
# -------------------------------
synergy_traits, power_traits = [], []
for trait in latest_set.get("traits", []):
    tid = trait.get("apiName", "")
    tname = localize_name(trait.get("name", ""))
    if not is_real_trait(tid, tname):
        continue
    packet = {
        "id": tid,
        "name": tname,
        "desc": trait.get("desc", ""),
        "effects": trait.get("effects", []),
    }
    if any(k in tid for k in ["PowerUp", "MechanicTrait", "Upgrade", "Destroyer", "Mentor"]):
        power_traits.append(packet)
    else:
        synergy_traits.append(packet)

# -------------------------------
# 6) 아이템 (현재 세트 + 공용) - ★사용자 제공 목록 기반 필터링 적용★
# -------------------------------
items = []
for item in data.get("items", []):
    # is_real_item 함수 내에서 ALLOWED_ITEM_NAMES 목록을 사용하여 필터링합니다.
    if not is_real_item(item):
        continue
    
    api = item.get("apiName", "")
    name = localize_name(item.get("name", ""))

    items.append({
        "id": api,
        "name": name,
        "from": item.get("from", []),
        "desc": item.get("desc", ""),
        "effects": item.get("effects", {}),
        "unique": item.get("unique", False),
    })

# -------------------------------
# 7) 증강 (augments) — JSON 전체 탐색 + null 제거 + 세트 버전 필터
# -------------------------------
augments = []

def walk_json(obj):
    """JSON 객체를 순회하며 모든 노드를 반환"""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from walk_json(v)
    elif isinstance(obj, list):
        for x in obj:
            yield from walk_json(x)
    yield obj

def valid_string(s):
    return bool(s and isinstance(s, str) and s.strip().lower() not in ["null", "none", "undefined"])

# 🔍 JSON 전체 순회
candidates = []
for node in walk_json(data):
    # 상단에 정의된 is_real_augment를 사용합니다.
    if isinstance(node, dict) and is_real_augment(node):
        candidates.append(node)

print(f"🧩 전체에서 증강 후보 {len(candidates)}개 발견됨 (TFT{set_number} 전용)")

seen = set()
for aug in candidates:
    api = aug.get("apiName", "")
    if api in seen:
        continue
    seen.add(api)

    name = localize_name(aug.get("name", ""))
    desc = aug.get("desc", "")
    # 상단에 정의된 normalize_tier를 사용합니다.
    tier = normalize_tier(aug.get("tier"))
    effects = aug.get("effects", {}) or aug.get("variables", {}) or {}
    associated = aug.get("associatedTraits", [])

    # ❌ null / 빈 데이터 제거
    if not valid_string(name): continue
    if not valid_string(desc): continue
    if not isinstance(effects, dict): continue
    if len(effects) == 0 and not associated: continue

    augments.append({
        "id": api,
        "name": name,
        "tier": tier,
        "desc": desc.strip(),
        "effects": effects,
        "traits": associated
    })

print(f"✅ 증강 {len(augments)}개 최종 추출 완료! (TFT{set_number} 기준 / 이전 세트 제거됨)")


# -------------------------------
# 8) 저장
# -------------------------------
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_json(filename, content):
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

save_json("champions.json", champions)
save_json("synergy_traits.json", synergy_traits)
save_json("power_traits.json", power_traits)
save_json("items.json", items)
save_json("augments.json", augments) 

# -------------------------------
# 8) 저장 (JSON 파일)
# -------------------------------
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_json(filename, content):
    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

save_json("champions.json", champions)
save_json("synergy_traits.json", synergy_traits)
save_json("power_traits.json", power_traits)
save_json("items.json", items)
save_json("augments.json", augments) 

# ----------------------------------------------------
# 🌟 9) 머신러닝 피처 엔지니어링 (추가된 ML 전처리 단계)
# ----------------------------------------------------
print("\n--- 🧠 머신러닝 피처 엔지니어링 시작 ---")

# A. 챔피언 시너지 유사도 모델을 위한 데이터 준비
df_champions = pd.DataFrame(champions)

if not df_champions.empty:
    # 1. 챔피언 특성 원-핫 인코딩
    print("  -> 챔피언 특성 원-핫 인코딩 중...")
    
    # traits 리스트를 딕셔너리로 변환하여 각 특성을 열로 만듭니다.
    trait_dummies = df_champions['traits'].apply(lambda x: {t: 1 for t in x}).apply(pd.Series).fillna(0)
    
    # 챔피언 기본 정보와 원-핫 인코딩된 특성을 결합
    df_champs_synergy = pd.concat([
        df_champions[['id', 'name', 'cost', 'ability']],
        trait_dummies
    ], axis=1)

    print(f"  ✅ 챔피언 시너지 피처 DataFrame 준비 완료. (형태: {df_champs_synergy.shape})")
    print(f"  (사용 가능한 특성 열 개수: {len(trait_dummies.columns)})")
else:
    print("  ⚠️ 챔피언 데이터가 비어 있어 시너지 피처 생성을 건너뜁니다.")


# B. 아이템 추천 모델을 위한 데이터 준비
df_items = pd.DataFrame(items)

if not df_items.empty:
    # 2. 아이템 효과 수치화 (effects 딕셔너리 정규화)
    print("  -> 아이템 효과 수치 정규화 중...")
    
    # effects 딕셔너리를 열로 펼칩니다 (JSON Normalization).
    df_items_effects = pd.json_normalize(df_items['effects']).fillna(0)
    
    # 챔피언-아이템 분류 모델에 사용할 아이템 데이터셋 생성
    df_items_for_itemization = pd.concat([
        df_items[['id', 'name', 'from', 'unique']], 
        df_items_effects
    ], axis=1)

    # 불필요한 API 해시 키 제거 (예: {1543aa48}와 같이 중괄호로 시작하는 키)
    cols_to_keep = [col for col in df_items_for_itemization.columns if not (isinstance(col, str) and col.startswith('{'))]
    df_items_for_itemization = df_items_for_itemization[cols_to_keep]

    print(f"  ✅ 아이템 효과 피처 DataFrame 준비 완료. (형태: {df_items_for_itemization.shape})")
    print(f"  (사용 가능한 아이템 스탯 열 개수: {len(df_items_for_itemization.columns) - 4})") # 4는 id, name, from, unique
else:
    print("  ⚠️ 아이템 데이터가 비어 있어 아이템 피처 생성을 건너뜁니다.")


print("\n--- 🏁 최종 결과 요약 ---")
print(f"세트명: {set_name} (TFT{set_number})")
print(f"챔피언 {len(champions)}명 / 시너지 {len(synergy_traits)}개 / 파워업 {len(power_traits)}개 / 증강 {len(augments)}개 / 아이템 {len(items)}개")

if 'df_champs_synergy' in locals():
    print(f"\n[ML-Ready] 챔피언 시너지 피처 (유사도 모델): {df_champs_synergy.shape}")
if 'df_items_for_itemization' in locals():
    print(f"[ML-Ready] 아이템 효과 피처 (분류 모델): {df_items_for_itemization.shape}")

print("\n--- 샘플 출력 (시너지 피처) ---")
if 'df_champs_synergy' in locals() and not df_champs_synergy.empty:
    print(df_champs_synergy[['name', 'cost'] + list(trait_dummies.columns[:5])].head(3).to_markdown(index=False))
else:
    print("샘플 데이터 없음.")

print("\n샘플 챔피언 3명:")
for c in champions[:3]:
    print(f" - {c['id']} ({c['name']}) {c['traits']}")

print("\n샘플 시너지 3개:")
for t in synergy_traits[:3]:
    print(f" - {t['id']} ({t['name']})")

print("\n샘플 파워업 3개:")
for t in power_traits[:3]:
    print(f" - {t['id']} ({t['name']})")

print("\n샘플 증강 5개:")
for a in augments[:5]:
    print(f" - [{a.get('tier')}] {a['id']} ({a['name']})")

print("\n샘플 아이템 5개:")
for i in items[:]:
    print(f" - {i['id']} ({i['name']})")