import json
import random
import re

# --- 1. 학습/추천 데이터 (CHAMPION_DATA_STRING) ---
CHAMPION_DATA_STRING = """
{
  "가렌": {"keywords": ["가렌", "garen"], "description": "가렌은 전투사관학교, 요새 시너지를 가진 탱커입니다.", "deck": [{"core": ["가렌", "레오나"], "synergy": ["요새", "전투사관학교"], "comment": "튼튼한 요새 앞라인 덱입니다."}]},
  "자이라": {"keywords": ["자이라", "zyra"], "description": "자이라는 수정 갬빗, 장미 어머니 시너지를 가진 마법사입니다.", "deck": [{"core": ["자이라", "바이", "스웨인"], "synergy": ["수정 갬빗", "마법사"], "comment": "수정 갬빗으로 CC와 딜을 넣습니다."}]},
  "아트록스": {"keywords": ["아트록스", "아트", "aatrox"], "description": "아트록스는 헤비급, 전쟁기계 시너지를 가진 탱커입니다.", "deck": [{"core": ["아트록스", "다리우스", "카타리나"], "synergy": ["헤비급", "전쟁기계"], "comment": "헤비급으로 초반부터 강력하게 압박하는 AD 딜러 덱입니다."}]},
  "잔나": {"keywords": ["잔나", "janna"], "description": "잔나는 수정 갬빗, 봉쇄자, 책략가 시너지를 가진 마법사입니다.", "deck": [{"core": ["잔나", "라이즈", "직스"], "synergy": ["책략가", "수정 갬빗"], "comment": "책략가 시너지를 활용하는 마법 딜러입니다."}]}
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
        "👶 **롤토체스를 처음 시작하시는 분들을 위한 추천 덱 (3가지)** 👶",
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
            "name": "별 수호자 덱",
            "core": ["렐", "니코", "세라핀","신드라","아리","뽀삐","자야","징크스"],
            "tip": "쉬운 아이템 조합과 안정적인 덱 전개로 초보자에게 추천돼요!"
        },
        {
            "name": "소울파이터 덱",
            "core": ["나피리", "사미라", "세트","비에고","럭스","그웬","신 짜오","볼리베어"],
            "tip": "체력이 높고 조합이 단순해서 입문자에게 좋아요!"
        },
        {
            "name": "요새 덱",
            "core": ["가렌", "레오나", "스웨인","쉔","신 짜오","자야","렐"],
            "tip": "탱커로 구성된 앞라인이 단단해서 안정적인 플레이가 가능합니다!"
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
