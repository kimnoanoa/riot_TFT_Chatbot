import json
import os
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np

# --- 설정 (JSON 파일 경로를 'data/' 폴더 기준으로 수정) ---
CHAMPION_FILE = "data/champions.json"
ITEM_FILE = "data/items.json"
SYNERGY_FILE = "data/synergy_traits.json"
AUGMENT_FILE = "data/augments.json"

# --- 헬퍼 함수: JSON 로드 ---
def load_json_data(filepath):
    """지정된 경로에서 JSON 파일을 안전하게 로드합니다."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️ 에러: 필수 파일 '{filepath}'을 찾을 수 없습니다. 정제 단계가 완료되었는지 확인하세요.")
        return None
    except json.JSONDecodeError:
        print(f"⚠️ 에러: 파일 '{filepath}'의 JSON 형식이 잘못되었습니다.")
        return None

# --- 데이터프레임 재구성 (이전 단계의 피처 엔지니어링 재현) ---

def reconstruct_champions_df(champions_data):
    """챔피언 데이터로 시너지 원-핫 인코딩 DataFrame을 만듭니다."""
    if not champions_data:
        return pd.DataFrame()
        
    df_champions = pd.DataFrame(champions_data)

    # 1. 챔피언 특성 원-핫 인코딩
    trait_dummies = df_champions['traits'].apply(lambda x: {t: 1 for t in x}).apply(pd.Series).fillna(0)
    
    # 챔피언 기본 정보와 원-핫 인코딩된 특성을 결합
    df_champs_synergy = pd.concat([
        df_champions[['id', 'name', 'cost']],
        trait_dummies
    ], axis=1)
    
    return df_champs_synergy

def reconstruct_items_df(items_data):
    """아이템 데이터로 스탯 정규화 DataFrame을 만듭니다."""
    if not items_data:
        return pd.DataFrame()
        
    df_items = pd.DataFrame(items_data)

    # 2. 아이템 효과 수치화 (effects 딕셔너리 정규화)
    df_items_effects = pd.json_normalize(df_items['effects']).fillna(0)
    
    df_items_for_itemization = pd.concat([
        df_items[['id', 'name']], 
        df_items_effects
    ], axis=1)

    # 불필요한 API 해시 키 제거 (중괄호로 시작하는 열)
    cols_to_keep = [col for col in df_items_for_itemization.columns if not (isinstance(col, str) and col.startswith('{'))]
    df_items_for_itemization = df_items_for_itemization[cols_to_keep]
    
    return df_items_for_itemization.reset_index(drop=True)


# =================================================================
# 🌟 테스트 함수 1: 코사인 유사도를 이용한 챔피언 추천
# =================================================================
def test_champion_similarity(df, target_champion_name="아트록스", top_n=5):
    """특정 챔피언과 시너지 특성이 가장 유사한 챔피언을 찾고 결과를 반환합니다."""
    
    # 챔피언 이름과 id 열을 제외한 특성 열만 선택합니다.
    feature_cols = df.columns.drop(['id', 'name', 'cost'])
    
    if df.empty or target_champion_name not in df['name'].values or feature_cols.empty:
        if "__main__" in globals() and __name__ == "__main__": # 메인 실행 시에만 출력
            print("\n" + "="*50)
            print(f"🥇 1. 챔피언 시너지 유사도 분석: '{target_champion_name}' 기준")
            print("="*50)
            print(f"⚠️ 데이터가 비어있거나 '{target_champion_name}' 챔피언을 찾을 수 없습니다.")
        return pd.DataFrame()

    # 피처 벡터 추출
    X = df[feature_cols].values
    
    # 대상 챔피언의 인덱스 찾기
    target_idx = df[df['name'] == target_champion_name].index[0]
    target_vector = X[target_idx].reshape(1, -1)
    
    # 코사인 유사도 계산
    similarity_scores = cosine_similarity(target_vector, X)
    
    # 결과를 DataFrame으로 변환
    similarity_df = pd.DataFrame({
        'name': df['name'],
        'score': similarity_scores[0],
        'traits': df[feature_cols].apply(lambda row: [c for c in feature_cols if row[c] == 1], axis=1)
    })
    
    # 자기 자신을 제외하고 점수가 높은 순으로 정렬
    result = similarity_df[similarity_df['name'] != target_champion_name].sort_values(by='score', ascending=False).head(top_n)

    if "__main__" in globals() and __name__ == "__main__": # 메인 실행 시에만 출력
        print("\n" + "="*50)
        print(f"🥇 1. 챔피언 시너지 유사도 분석: '{target_champion_name}' 기준")
        print("="*50)
        print(f"특성 벡터를 기반으로 '{target_champion_name}'와 시너지가 가장 유사한 챔피언:")
        print("---------------------------------------------------------------------")
        for _, row in result.iterrows():
            traits_str = ', '.join(row['traits'])
            print(f"  - {row['name']:8s} (유사도: {row['score']:.4f}) | 시너지: [{traits_str}]")
            
    return result

# =================================================================
# 🌟 테스트 함수 2: K-Means를 이용한 아이템 군집화
# =================================================================
def test_item_clustering(df, n_clusters=3):
    """아이템 스탯을 기반으로 K-Means 군집 분석을 수행하여 아이템 유형을 분류하고 결과를 반환합니다."""
    
    if "__main__" in globals() and __name__ == "__main__":
        print("\n" + "="*50)
        print(f"🥈 2. 아이템 스탯 기반 군집화 ({n_clusters}개 그룹)")
        print("="*50)

    if df.empty:
        if "__main__" in globals() and __name__ == "__main__":
            print("⚠️ 아이템 데이터가 비어 있어 군집화 분석을 건너뜁니다.")
        return pd.DataFrame()

    # --- 핵심 스탯 정의 ---
    CORE_STATS = [
        'AD', 'AP', 'AS', 'CritChance', 
        'Health', 'Armor', 'MagicResist', 'Mana', 
        'ManaRestore', 'OmniVamp', 'HealOnHit', 'AttackRange'
    ]
    
    feature_cols = [col for col in CORE_STATS if col in df.columns]
    
    df_filtered = df[~df['name'].str.contains(' 상징')].copy()
    df_filtered = df_filtered[df_filtered[feature_cols].sum(axis=1) > 0].copy()
    
    X = df_filtered[feature_cols].values

    if X.shape[0] < n_clusters:
        if "__main__" in globals() and __name__ == "__main__":
            print(f"⚠️ 유효 아이템 개수({X.shape[0]})가 군집 수({n_clusters})보다 적습니다. 군집화를 건너킵니다.")
        return pd.DataFrame()

    # 스케일링 및 K-Means 학습
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
    df_filtered['cluster'] = kmeans.fit_predict(X_scaled)
    df_filtered['cluster_label'] = ""

    # 클러스터 이름 결정 및 출력
    for i in range(n_clusters):
        cluster_items = df_filtered[df_filtered['cluster'] == i]['name'].tolist()
        centroid = scaler.inverse_transform(kmeans.cluster_centers_[i].reshape(1, -1))[0]
        centroid_stats_series = pd.Series(centroid, index=feature_cols).sort_values(ascending=False)
        top_stat = centroid_stats_series.index[0]
        top_3_stats = centroid_stats_series.head(3)
        
        damage_stats = ['AD', 'AP', 'AS', 'CritChance']
        tank_stats = ['Health', 'Armor', 'MagicResist']
        
        damage_count = sum(1 for stat in top_3_stats.index if stat in damage_stats)
        tank_count = sum(1 for stat in top_3_stats.index if stat in tank_stats)
        
        current_cluster_name = f"기타/유틸리티 ({top_stat} 지향)"
        
        if damage_count >= 2 and ('AP' in top_3_stats.index or 'Mana' in top_3_stats.index):
            current_cluster_name = f"AP/마법력 ({top_stat} 지향)"
        elif damage_count >= 2 and ('AD' in top_3_stats.index or 'AS' in top_3_stats.index):
            current_cluster_name = f"AD/공격력 ({top_stat} 지향)"
        elif tank_count >= 2:
            current_cluster_name = f"탱킹/방어 ({top_stat} 지향)"
        
        df_filtered.loc[df_filtered['cluster'] == i, 'cluster_label'] = current_cluster_name

        if "__main__" in globals() and __name__ == "__main__":
            print(f"\n--- {current_cluster_name} ({len(cluster_items)}개 아이템) ---")
            print(f"  >> 대표 스탯(가장 높은 평균값): {', '.join([f'{k}: {v:.1f}' for k, v in top_3_stats.items()])}")
            print("  >> 아이템 목록:", end=" ")
            print(', '.join(cluster_items))
            
    return df_filtered

# =================================================================
# 🌟 테스트 함수 3: 챔피언 기반 챗봇 기능 시뮬레이션
# =================================================================
def simulate_tft_chatbot(df_champs, df_items_clustered, target_champion_name="우디르"):
    """
    챔피언의 특성을 기반으로 시너지 추천 및 아이템 그룹 추천을 시뮬레이션합니다.
    """
    
    print("\n" + "="*50)
    print(f"🥉 3. 챔피언 기반 챗봇 기능 시뮬레이션: '{target_champion_name}'")
    print("="*50)
    
    if df_champs.empty or target_champion_name not in df_champs['name'].values:
        print(f"⚠️ 챔피언 '{target_champion_name}'에 대한 데이터가 불충분합니다.")
        return
        
    # 1. 챔피언의 기본 정보와 특성 파악
    champ_data = df_champs[df_champs['name'] == target_champion_name].iloc[0]
    traits = [col for col in df_champs.columns.drop(['id', 'name', 'cost']) if champ_data[col] == 1]
    
    # 2. 시너지 추천 (가장 유사한 챔피언 찾기)
    # 챗봇 응답을 위해 3개만 요청합니다.
    similar_champs_df = test_champion_similarity(df_champs, target_champion_name, top_n=3)
    
    # 3. 아이템 추천 그룹 결정 (간단한 휴리스틱)
    
    # 특성을 기반으로 챔피언의 주 포지션 추론
    is_ap = any(t in traits for t in ['마법사', '별 수호자', '책략가'])
    is_ad = any(t in traits for t in ['저격수', '이단아', '타격대', '프로레슬러', '전쟁기계'])
    is_tank = any(t in traits for t in ['헤비급', '거대 메크', '요새', '파수꾼', '돌격대', '멘토']) # '멘토' 추가
    
    item_type_recommendation = []
    
    if is_tank:
        item_type_recommendation.append('탱킹/방어')
        
    if is_ap:
        item_type_recommendation.append('AP/마법력')
    elif is_ad:
        item_type_recommendation.append('AD/공격력')
    
    # 특성만으로 판단이 어려운 경우 혹은 하이브리드일 경우
    if not item_type_recommendation:
        item_type_recommendation = ['AP/마법력', 'AD/공격력', '탱킹/방어'] # 기본값 (모두)

    item_type_recommendation = list(set(item_type_recommendation))

    # 4. 챗봇 응답 형식으로 결과 출력
    
    print(f"\n==================================================")
    print(f"🗣️ 챗봇 시뮬레이션 응답 (대상: {target_champion_name})")
    print(f"==================================================")
    
    # Q1. 어떤 덱 가는 게 좋을까? (주력 시너지 확인)
    print(f"Q: '{target_champion_name}' 떴는데 어떤 덱 가는 게 좋을까?")
    print(f"A: {target_champion_name} 챔피언의 주력 특성은 **{', '.join(traits)}**입니다.")
    if len(traits) >= 2:
        print(f"이 특성들을 기반으로 **{traits[0]}** 또는 **{traits[1]}** 덱의 초반 빌드업을 추천합니다.")
    else:
        print(f"이 특성을 기반으로 **{traits[0]}** 덱을 중심으로 빌드업을 시작하는 것을 추천합니다.")
    
    print("-" * 30)
    
    # Q2. 템 뭐 넣는 게 좋아? (아이템 그룹 추천)
    print(f"Q: '{target_champion_name}'한테 템 뭐 넣는 게 좋아?")
    print(f"A: {target_champion_name}의 특성({', '.join(traits)}) 분석 결과, 주로 **{' 및 '.join(item_type_recommendation)}** 유형의 아이템이 잘 맞습니다.")
    
    recommended_items = []
    for type_name in item_type_recommendation:
        if df_items_clustered.empty: continue
        
        # 클러스터 레이블을 포함하는 정확한 이름 찾기
        cluster_name_match = [label for label in df_items_clustered['cluster_label'].unique() if type_name in label]
        
        if cluster_name_match:
            # 해당 클러스터에서 임의로 3개 아이템을 추출 (예시)
            # 이름이 '도적의 장갑' 처럼 중복되는 아이템이 있으므로 set으로 중복 제거 후 추출
            items = df_items_clustered[df_items_clustered['cluster_label'] == cluster_name_match[0]]['name']
            recommended_items.extend(list(set(items.tolist()))[:3])
    
    if recommended_items:
        print(f"   - 추천 아이템(예시): **{', '.join(list(set(recommended_items)))}** 등")
    else:
        print(f"   - 현재 아이템 데이터 분석으로는 명확한 추천 아이템을 찾기 어렵습니다. 아이템 클러스터링 결과를 먼저 확인해주세요.")

    print("-" * 30)
    
    # Q3. 같이 갈 시너지 덱으로 뭘 추천해? (유사 챔피언 추천)
    print(f"Q: '{target_champion_name}'랑 같이 갈 시너지 덱으로 뭘 추천해?")
    
    if not similar_champs_df.empty:
        print(f"A: {target_champion_name}와 특성 구성이 유사하여 함께 사용하기 좋은 챔피언들은 다음과 같습니다 (유사도 순):")
        for _, row in similar_champs_df.iterrows():
            traits_str = ', '.join(row['traits'])
            print(f"   - **{row['name']}**: 시너지 [{traits_str}]")
    else:
        print(f"A: 시너지 유사도 분석을 위한 데이터가 부족합니다.")
        
    print(f"==================================================\n")

# =================================================================
# 🌟 메인 실행 블록
# =================================================================
if __name__ == "__main__":
    
    print("🚀 TFT 데이터 분석 테스트 시작...")

    # 1. 데이터 로드
    champions_data = load_json_data(CHAMPION_FILE)
    items_data = load_json_data(ITEM_FILE)

    if not champions_data or not items_data:
        print("필수 데이터 파일 로드 실패. 테스트를 종료합니다.")
    else:
        # 2. DataFrame 재구성
        df_champs_synergy = reconstruct_champions_df(champions_data)
        df_items_for_itemization = reconstruct_items_df(items_data)

        # 3. 테스트 실행 (기존 테스트)
        # 챔피언 유사도 분석 결과를 챗봇 시뮬레이션에 사용하기 위해 변수로 받습니다.
        df_similar_champs = test_champion_similarity(df_champs_synergy, target_champion_name="아트록스")
        # 아이템 군집화 결과를 챗봇 시뮬레이션에 사용하기 위해 변수로 받습니다.
        df_items_clustered = test_item_clustering(df_items_for_itemization, n_clusters=3)
        
        # 4. 챗봇 기능 시뮬레이션 (새로운 테스트)
        # 챔피언 '우디르'에 대한 챗봇 기능 시뮬레이션을 실행합니다.
        simulate_tft_chatbot(df_champs_synergy, df_items_clustered, target_champion_name="트위스티드 페이트")

    print("\n✅ 모든 테스트 완료.")