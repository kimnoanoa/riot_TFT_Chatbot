import json
import random
import re

# --- 1. 학습/추천 데이터 (CHAMPION_DATA_STRING) ---
CHAMPION_DATA_STRING = """
{
  "가렌": {
    "keywords": ["가렌", "garen"],
    "description": "가렌은 전방에서 피해를 흡수하는 탱커형 챔피언으로, 단단한 앞라인을 구성하는 데 적합합니다.",
    "deck": [
      {
        "core": ["가렌", "레오나", "쉔"],
        "synergy": ["탱커 중심"],
        "comment": "앞라인을 단단하게 세워 딜러를 보호하는 초보자용 안정 덱입니다."
      }
    ]
  },

  "럭스": {
    "keywords": ["럭스", "lux"],
    "description": "럭스는 주문력(AP) 기반 스킬 피해를 주는 마법사 챔피언입니다.",
    "deck": [
      {
        "core": ["럭스", "세라핀", "갈리오"],
        "synergy": ["AP 중심"],
        "comment": "스킬 피해 위주의 AP 덱으로, 아이템만 맞으면 후반 화력이 강합니다."
      }
    ]
  },

  "카이사": {
    "keywords": ["카이사", "kai'sa", "kaisa"],
    "description": "카이사는 후반 캐리력이 뛰어난 딜러로, 공격 속도와 주문력 모두 활용할 수 있습니다.",
    "deck": [
      {
        "core": ["카이사", "말자하", "초가스"],
        "synergy": ["후반 캐리"],
        "comment": "후반을 바라보는 성장형 덱으로, 아이템이 갖춰지면 폭발력이 큽니다."
      }
    ]
  },

  "야스오": {
    "keywords": ["야스오", "yasuo"],
    "description": "야스오는 근접 전투에 특화된 딜러로, 빠른 공격과 연속 전투에 강합니다.",
    "deck": [
      {
        "core": ["야스오", "쉔", "오공"],
        "synergy": ["근접 딜러"],
        "comment": "전면 압박이 강한 조합으로, 초중반 전투에서 우위를 점하기 좋습니다."
      }
    ]
  }
}

""" 
CHAMPION_DATA_GLOBAL = json.loads(CHAMPION_DATA_STRING)


# --- 2. 초보자용 덱 요약 설명 ---
def recommend_newbie_deck_expanded(champion_data):
    """
    미리 정의된 3가지 초보자 덱을 설명 형태로 출력 (단순 안내용)
    """
    deck1 = champion_data.get("가렌")
    deck2 = champion_data.get("자이라")
    deck3 = champion_data.get("아트록스")

    if not (deck1 and deck2 and deck3):
        return "⚠️ 초보자 추천 덱 데이터를 찾을 수 없습니다."

    d1, d2, d3 = deck1["deck"][0], deck2["deck"][0], deck3["deck"][0]
    text = [
        "👶 **롤토체스를 처음 시작하시는 분들을 위한 추천 덱 (5가지)** 👶",
        "",
        f"1️⃣ {d1['core'][0]} 덱 — {', '.join(d1['core'])}\n   💡 {d1['comment']}",
        f"2️⃣ {d3['core'][0]} 덱 — {', '.join(d3['core'])}\n   💡 {d3['comment']}",
        f"3️⃣ {d2['core'][0]} 덱 — {', '.join(d2['core'])}\n   💡 {d2['comment']}"
    ]
    return "\n".join(text)


# --- 3. 초보자 덱 추천 함수 (중복 방지 포함) ---
def get_beginner_deck_recommendation(last_recommended=None):
    """
    초보자용 덱을 랜덤으로 추천하되,
    직전에 추천된 덱은 제외한다.
    """

    decks = [
    {
        "name": "빌지워터 플릿 덱",
        "core": ["노틸러스", "타릭", "루시안", "세나", "미스 포츈", "징크스", "갈리오", "헤카림"],
        "tip": "초반 골드 운영이 안정적이고, 후반 캐리력이 좋은 덱입니다."
    },
    {
        "name": "AP 중심 루시안 덱",
        "core": ["루시안", "세나", "말자하", "럭스", "갈리오", "애쉬", "타릭"],
        "tip": "루시안과 세나를 중심으로 한 균형 잡힌 AP/AD 혼합 덱입니다."
    },
    {
        "name": "아이오니아 탱/서포터 덱",
        "core": ["쉔", "세라핀", "유미", "아리", "오공", "사이온", "베인"],
        "tip": "탱커와 서포터 위주의 안정적인 조합으로 초보자에게 추천됩니다."
    },
    {
        "name": "프렐요드 탱/AD 덱",
        "core": ["볼리베어", "애쉬", "트린다미어", "레넥톤", "가렌", "세주아니", "노틸러스"],
        "tip": "앞라인이 단단하고 AD 딜러 중심으로 운영하기 쉬운 덱입니다."
    },
    {
        "name": "후반 캐리 딜러 덱",
        "core": ["카이사", "말자하", "초가스", "코그모", "아펠리오스", "에코"],
        "tip": "후반으로 갈수록 강해지는 성장형 덱으로 고점을 노릴 수 있습니다."
    }
    ]


    # ✅ 직전 덱 제외
    available = [d for d in decks if d["name"] != last_recommended]
    if not available:
        return "✅ 모든 초보자용 덱을 이미 보셨습니다!\n다른 챔피언 기반 덱을 추천받아보세요 🙂"

    pick = random.choice(available)
    return (
        f"🎯 초보자용 추천 덱: {pick['name']}\n"
        f"⭐ 핵심 챔피언: {', '.join(pick['core'])}\n"
        f"💡 팁: {pick['tip']}"
    )


# --- 4. 테스트 실행용 ---
if __name__ == "__main__":
    print("=== 첫 번째 추천 ===")
    first = get_beginner_deck_recommendation()
    print(first)

    print("\n=== 두 번째 추천 (중복 방지) ===")
    # 마지막 덱 이름 추출
    match = re.search(r"추천 덱: (.+?)\n", first)
    last_name = match.group(1).strip() if match else None
    print(get_beginner_deck_recommendation(last_name))
