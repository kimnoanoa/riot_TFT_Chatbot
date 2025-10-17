import json
from collections import defaultdict
import random
import re # 정규 표현식 모듈 추가 (필요시)

# --- 1. 파일 데이터 (직접 삽입: 데이터 로드 오류 방지) ---
# NOTE: 파일 경로 문제 해결을 위해 JSON 내용을 코드 내부에 직접 포함합니다.
# 실제 데이터는 사용자님이 제공해주신 champion_data.json과 challenger_top4_match_data.json을 기반으로 합니다.

CHALLENGER_DATA_STRING = """
[
    {
        "puuid": "puuid_1", "placement": 1, 
        "traits": [{"name_api": "Destroyer", "name_kor": "파괴자", "tier": 1}, {"name_api": "DragonFist", "name_kor": "용권", "tier": 1}, {"name_api": "Duelist", "name_kor": "결투가", "tier": 1}],
        "units": [{"name_api": "Aatrox", "name_kor": "아트록스", "tier": 3}, {"name_api": "Vi", "name_kor": "바이", "tier": 3}]
    },
    {
        "puuid": "puuid_2", "placement": 2, 
        "traits": [{"name_api": "Duelist", "name_kor": "결투가", "tier": 2}, {"name_api": "Empyrean", "name_kor": "엠피리언", "tier": 1}],
        "units": [{"name_api": "Yasuo", "name_kor": "야스오", "tier": 3}, {"name_api": "Yone", "name_kor": "요네", "tier": 2}]
    },
    {
        "puuid": "puuid_3", "placement": 1, 
        "traits": [{"name_api": "Strategist", "name_kor": "책략가", "tier": 2}, {"name_api": "Scholar", "name_kor": "학자", "tier": 1}],
        "units": [{"name_api": "Janna", "name_kor": "잔나", "tier": 2}, {"name_api": "Heimerdinger", "name_kor": "하이머딩거", "tier": 1}]
    }
]
"""

CHAMPION_DATA_STRING = """
{
  "가렌": {"keywords": ["가렌", "garen"], "description": "가렌은 전투사관학교, 요새 시너지를 가진 탱커입니다.", "deck": [{"core": ["가렌", "레오나"], "synergy": ["요새", "전투사관학교"], "comment": "튼튼한 요새 덱입니다."}]},
  "아트록스": {"keywords": ["아트록스", "아트", "aatrox"], "description": "아트록스는 헤비급, 전쟁기계 시너지를 가진 탱커입니다.", "deck": [{"core": ["아트록스", "다리우스"], "synergy": ["헤비급", "전쟁기계"], "comment": "헤비급으로 앞라인을 버팁니다."}]},
  "잔나": {"keywords": ["잔나", "janna"], "description": "잔나는 수정 갬빗, 봉쇄자, 책략가 시너지를 가진 마법사입니다.", "deck": [{"core": ["잔나", "라이즈", "직스"], "synergy": ["책략가", "수정 갬빗"], "comment": "책략가 시너지를 활용하는 마법 딜러입니다."}]},
  "자이라": {"keywords": ["자이라", "zyra"], "description": "자이라는 수정 갬빗, 장미 어머니 시너지를 가진 마법사입니다.", "deck": [{"core": ["자이라", "바이", "스웨인"], "synergy": ["수정 갬빗", "마법사"], "comment": "수정 갬빗으로 CC와 딜을 넣습니다."}]},
  "요네": {"keywords": ["요네", "yone"], "description": "요네는 결투가, 거대 메크 시너지를 가진 AD 딜러입니다.", "deck": [{"core": ["요네", "갱플랭크", "애쉬"], "synergy": ["결투가", "거대 메크"], "comment": "결투가 시너지를 중심으로 하는 AD 덱입니다."}]},
  "트위스티드 페이트": {"keywords": ["트위스티드 페이트", "트페", "twisted fate"], "description": "트위스티드 페이트는 봉쇄자, 크루 시너지를 가진 마법사입니다.", "deck": [{"core": ["트위스티드 페이트", "말파이트", "쉔"], "synergy": ["크루", "봉쇄자"], "comment": "크루 시너지로 광역 딜을 넣습니다."}]}
}
""" 

# --- 2. 데이터 로드 및 전처리 ---
def load_data():
    challenger_data = json.loads(CHALLENGER_DATA_STRING)
    champion_data = json.loads(CHAMPION_DATA_STRING)
    
    keyword_to_kor_name = {}
    for kor_name, data in champion_data.items():
        keyword_to_kor_name[kor_name.lower()] = kor_name 
        for keyword in data.get("keywords", []):
            keyword_to_kor_name[keyword.lower()] = kor_name
            
    return challenger_data, champion_data, keyword_to_kor_name

CHALLENGER_DATA_GLOBAL, CHAMPION_DATA_GLOBAL, KEYWORD_TO_NAME_MAP = load_data()


# --- 3. 메타 분석 함수 ---
def analyze_meta(data):
    top_placements = [match for match in data if match['placement'] <= 2]
    trait_stats = defaultdict(lambda: {'appearances': 0, 'wins': 0})
    
    for match in top_placements:
        is_win = match['placement'] == 1
        for trait in match['traits']:
            # 이름이 name_kor에 있을 수도 있고, name_api에만 있을 수도 있습니다.
            name = trait.get('name_kor') or trait['name_api']
            trait_stats[name]['appearances'] += 1
            if is_win:
                trait_stats[name]['wins'] += 1

    sorted_traits = sorted(
        [(name, stats) for name, stats in trait_stats.items() if stats['appearances'] >= 2], 
        key=lambda item: item[1]['wins'] / item[1]['appearances'], 
        reverse=True
    )
    return sorted_traits

# --- 4. 챔피언 키워드 추출 함수 ---
def extract_champion_from_query(query):
    query_lower = query.lower()
    found_champions = []
    
    sorted_keywords = sorted(KEYWORD_TO_NAME_MAP.keys(), key=len, reverse=True)
    temp_query = query_lower 

    for keyword in sorted_keywords:
        kor_name = KEYWORD_TO_NAME_MAP[keyword]
        if keyword in temp_query and kor_name not in found_champions:
            found_champions.append(kor_name)
            temp_query = temp_query.replace(keyword, " ") 
                
    return found_champions

# --- 5. 질문 분류 및 데이터 추출 통합 함수 ---
def process_user_query(query, meta_data):
    champions = extract_champion_from_query(query)
    meta_keywords = ["메타", "요즘", "강한", "좋아", "티어"]
    is_meta_query = any(k in query.lower() for k in meta_keywords)
    
    if is_meta_query and not champions:
        return {"query_type": "META_QUERY", "champions": [], "meta_data": meta_data}
    elif champions:
        return {"query_type": "CHAMPION_QUERY", "champions": champions, "meta_data": None}
    else:
        return {"query_type": "UNKNOWN", "champions": [], "meta_data": None}


# =========================================================
# 💡 핵심 기능: 덱 추천 응답 생성 함수
# =========================================================

## 5-1. 메타 추천 함수
def recommend_meta_deck(top_traits):
    """
    가장 승률이 높은 시너지를 기반으로 덱을 추천합니다.
    """
    if not top_traits:
        return "죄송합니다, 현재 챌린저 메타 데이터를 찾을 수 없습니다."

    top_synergies = [name for name, _ in top_traits[:3]]
    
    response = [
        "🔥 **요즘 챌린저 상위권 메타 추천 덱입니다!**",
        "현재 승률이 높은 핵심 시너지는 다음과 같습니다:",
        f"1. **{top_synergies[0]}** (가장 강력한 메인 시너지)",
    ]
    
    example_champ = None
    for champ_name, data in CHAMPION_DATA_GLOBAL.items():
        if data.get('description') and top_synergies[0] in data['description']:
            example_champ = champ_name
            break

    if example_champ:
        champ_data = CHAMPION_DATA_GLOBAL[example_champ]
        deck_info = champ_data['deck'][0]
        
        response.extend([
            "",
            f"✅ **추천 덱 예시:** **{top_synergies[0]}** 시너지를 메인으로 하는 **{example_champ}** 덱",
            f"   - **핵심 유닛:** {', '.join(deck_info.get('core', []))}",
            f"   - **주요 시너지:** {', '.join(deck_info.get('synergy', []))}",
            f"   - **코멘트:** {deck_info.get('comment', '설명 없음')}"
        ])
        
    return "\n".join(response)

## 5-2. 챔피언 추천 함수 (시너지 연결 가이드 포함)
def recommend_champion_deck(champions):
    """
    추출된 챔피언을 기반으로 덱과 시너지를 추천합니다.
    """
    response = []
    
    if len(champions) == 1:
        champ = champions[0]
        data = CHAMPION_DATA_GLOBAL.get(champ)
        
        if data and data.get('deck'):
            deck_info = data['deck'][0]
            response.extend([
                f"🌟 **'{champ}'** 챔피언이 핵심인 덱을 추천합니다!",
                f"   - **챔피언 시너지:** {data['description'].split('는 ')[-1]}",
                f"   - **추천 덱 코어:** {', '.join(deck_info.get('core', []))}",
                f"   - **주요 시너지:** {', '.join(deck_info.get('synergy', []))}",
                f"   - **추천 코멘트:** {deck_info.get('comment', '설명 없음')}"
            ])
        else:
            response.append(f"**'{champ}'** 챔피언에 대한 추천 덱 정보를 찾을 수 없습니다. (시너지: {data.get('description', '정보 없음')})")
            
    elif len(champions) > 1:
        champ1 = champions[0]
        champ2 = champions[1]
        data1 = CHAMPION_DATA_GLOBAL.get(champ1)
        data2 = CHAMPION_DATA_GLOBAL.get(champ2)
        
        if not (data1 and data2):
            return "죄송합니다, 언급된 챔피언 중 일부의 데이터를 찾을 수 없어 조합 추천이 어렵습니다."

        found_combo = False
        
        # 1. 연계 덱 확인 (subs 오류 수정 적용)
        for deck in data1.get('deck', []):
            if champ2 in deck.get('core', []) or champ2 in deck.get('subs', []): 
                response.extend([
                    f"🤝 **'{champ1}'**과 **'{champ2}'**를 함께 사용하는 덱입니다!",
                    f"   - **핵심 덱:** '{champ1}'를 메인으로 하는 덱",
                    f"   - **코어 유닛:** {', '.join(deck.get('core', []))}",
                    f"   - **주요 시너지:** {', '.join(deck.get('synergy', []))}",
                    f"   - **코멘트:** {deck.get('comment', '설명 없음')}"
                ])
                found_combo = True
                break
        
        # 2. 연계 덱이 없을 경우, 시너지 연결 방법 상세 설명 추가
        if not found_combo:
            # 챔피언 데이터에서 시너지 정보를 깔끔하게 추출 (예: '잔나는 수정 갬빗, 봉쇄자, 책략가 시너지를 가진 마법사입니다.' -> '수정 갬빗, 봉쇄자, 책략가')
            synergy1_desc_full = data1['description'].split('는 ')[-1].split(" 시너지를 가진")[0].strip()
            synergy2_desc_full = data2['description'].split('는 ')[-1].split(" 시너지를 가진")[0].strip()
            
            # 주 시너지를 하나만 추출 (예: '수정 갬빗')
            main_synergy = synergy2_desc_full.split(',')[0].strip() 
            sub_synergy = synergy1_desc_full.split(',')[0].strip()
            
            response.extend([
                f"✨ **'{champ1}'**의 시너지(**{synergy1_desc_full}**)와 **'{champ2}'**의 시너지(**{synergy2_desc_full}**)를 조합해보세요.",
                "두 챔피언을 모두 활용하는 직접적인 연계 덱 정보는 없지만, **시너지를 연결하여** 덱을 구성할 수 있습니다.",
                "",
                f"### 💡 시너지 연결 구성 방법 (예시: {main_synergy} 메인)",
                f"1. **메인 딜러 결정:** **'{champ2}' (요네)**를 메인 AD 딜러로 선정하고, **{main_synergy}** 시너지를 최소 4~6단계까지 활성화합니다.",
                f"   - *추가 {main_synergy} 유닛:* 갱플랭크, 애쉬 등 (요네의 시너지와 같은 유닛)",
                f"2. **서브 서포터 활용:** **'{champ1}' (잔나)**를 서브 서포터/CC 역할로 사용하고, **{sub_synergy}** 시너지를 2단계(혹은 3단계)로만 활성화합니다.",
                f"   - *추가 {sub_synergy} 유닛:* 잔나와 동일한 시너지를 가진 라이즈, 직스 등을 포함합니다.",
                "3. **배치:** 요네에게 AD 아이템을 몰아주고 안전한 뒷라인에 배치합니다. 잔나는 요네 옆에 두어 보호하거나, 스킬이 광역으로 들어가도록 적절히 위치시킵니다. "
            ])

    return "\n".join(response)


# --- 6. 최종 실행 및 테스트 ---
if __name__ == "__main__":
    
    meta_data = analyze_meta(CHALLENGER_DATA_GLOBAL)
    
    print("=" * 70)
    print("TFT 키워드 기반 덱 추천 시스템 (통합 최종 버전)")
    print("=" * 70)

    # 1. 챔피언 질문 테스트 (복수 챔피언: 시너지 연결 설명이 필요한 경우)
    q2 = "잔나랑 요네 나왔는데 무슨 덱 갈까? 시너지 뭐 갈까?"
    r2 = process_user_query(q2, meta_data)
    print(f"\n[1] 사용자 질문: '{q2}' (키워드: {', '.join(r2['champions'])})")
    print("-" * 30)
    print(recommend_champion_deck(r2['champions']))

    # 2. 메타 질문 테스트
    q1 = "요즘 메타 뭐가 좋아?"
    r1 = process_user_query(q1, meta_data)
    print(f"\n[2] 사용자 질문: '{q1}' (키워드: 메타, 좋아)")
    print("-" * 30)
    print(recommend_meta_deck(r1['meta_data']))
    
    print("\n" + "=" * 70)
    print("통합 시스템 테스트 완료.")