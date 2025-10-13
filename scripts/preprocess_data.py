import json
import os

INPUT_PATH = "data/ko_kr.json"
OUTPUT_DIR = "data/"

# -------------------------------
# 1) 데이터 로드
# -------------------------------
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# -------------------------------
# 2) 최신 세트 자동 감지
# -------------------------------
set_list = data.get("setData", [])
if not set_list:
    raise ValueError("⚠️ setData가 비어 있습니다!")

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
    if isinstance(item, str): return False
    api = item.get("apiName", "")
    if not api: return False
    banned = [
        "Augment", "ArmoryKey", "TFT_Consumable", "TFT_Item_Tactician",
        "TFT_Item_Stage", "TFT_Item_Neeko", "PM_", "Orb", "Consumable"
    ]
    if any(b in api for b in banned): return False
    # 현재 세트 전용(TFT{n}_) 또는 공용 장비(TFT_Item_)만 허용
    if not (api.startswith(f"TFT{set_number}_") or api.startswith("TFT_Item_")):
        return False
    if not item.get("name"): return False
    return True

def is_real_augment(aug: dict):
    """증강만 따로: 현재 세트 또는 공용 증강 접두 허용"""
    if isinstance(aug, str):  # 혹시 문자열 id만 있을 경우 스킵
        return False
    api = aug.get("apiName", "")
    if not api:
        return False
    # 세트 접두(TFT{n}_) 또는 증강 공용 접두(TFT_Augment_) 허용
    if not (api.startswith(f"TFT{set_number}_") or api.startswith("TFT_Augment_")):
        return False
    banned = ["Test", "Tutorial", "Dev", "PM_", "EventPM"]
    if any(b in api for b in banned):
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
        # 숫자 스트링일 수도 있음
        if up.isdigit():
            return {"1":"Silver","2":"Gold","3":"Prismatic"}.get(up, up)
        return tier_value
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
# 6) 아이템 (현재 세트 + 공용)
# -------------------------------
items = []
for item in data.get("items", []):
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

def normalize_tier(tier_value):
    if tier_value is None:
        return None
    if isinstance(tier_value, str):
        t = tier_value.strip().lower()
        if "silver" in t: return "Silver"
        if "gold" in t: return "Gold"
        if "prismatic" in t or "chromatic" in t: return "Prismatic"
        if t.isdigit(): return {"1":"Silver","2":"Gold","3":"Prismatic"}.get(t, t)
        return tier_value
    if isinstance(tier_value, (int, float)):
        return {1:"Silver", 2:"Gold", 3:"Prismatic"}.get(int(tier_value), tier_value)
    return tier_value

def is_real_augment(aug):
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

def walk_json(obj):
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
save_json("augments.json", augments)   # ★증강 저장★

# -------------------------------
# 9) 결과 출력
# -------------------------------
print("\n✅ 데이터 정제 완료!")
print(f"세트명: {set_name} (TFT{set_number})")
print(f"챔피언 {len(champions)}명 / 시너지 {len(synergy_traits)}개 / 파워업 {len(power_traits)}개 / 증강 {len(augments)}개 / 아이템 {len(items)}개")

print("\n샘플 챔피언 3명:")
for c in champions[:10]:
    print(f" - {c['id']} ({c['name']})")

print("\n샘플 시너지 3개:")
for t in synergy_traits[:10]:
    print(f" - {t['id']} ({t['name']})")

print("\n샘플 파워업 3개:")
for t in power_traits[:10]:
    print(f" - {t['id']} ({t['name']})")

print("\n샘플 증강 5개:")
for a in augments[:38]:
    print(f" - [{a.get('tier')}] {a['id']} ({a['name']})")

print("\n샘플 아이템 5개:")
for i in items[:10]:
    print(f" - {i['id']} ({i['name']})")
