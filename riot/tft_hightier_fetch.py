import requests
import time
import os
import pandas as pd
import datetime as dt
from tabulate import tabulate

# ⚙️ 최신 API 키 입력 (매일 갱신 필요)
API_KEY = "RGAPI-9163dd26-25e7-4d1b-a419-2f8582d8ec2c"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-Riot-Token": API_KEY,
}

# =========================================
# 공통 요청 함수 (안정적 호출)
# =========================================
def get_r(url):
    while True:
        try:
            r = requests.get(url, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                return r
            elif r.status_code == 429:
                print("⚠️ 429 Too Many Requests → 10초 대기 중...")
                time.sleep(10)
                continue
            elif r.status_code in [502, 503]:
                print(f"⚠️ 서버 오류 {r.status_code}, 5초 후 재시도...")
                time.sleep(5)
                continue
            elif r.status_code in [403, 401]:
                print("❌ 인증 오류(API 키 만료 가능)")
                return None
            else:
                print(f"❌ HTTP {r.status_code} 오류 - {url}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"🔁 연결 오류: {e} → 5초 대기 후 재시도")
            time.sleep(5)

# =========================================
# Riot ID 조회 (puuid → gameName#tagLine)
# =========================================
def get_riot_name_by_puuid(puuid, region="asia"):
    if not puuid or len(puuid) < 30:
        return None

    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    r = get_r(url)
    if not r:
        return None

    data = r.json()
    game_name = data.get("gameName")
    tag_line = data.get("tagLine")
    if game_name and tag_line:
        return f"{game_name}#{tag_line}"
    return game_name or None

# =========================================
# TFT 티어별 데이터 가져오기
# =========================================
def get_tft_tier_data(tier):
    """
    tier: 'challenger', 'grandmaster', 'master'
    """
    print(f"\n🚀 {tier.title()} 데이터 수집 중...")
    url = f"https://kr.api.riotgames.com/tft/league/v1/{tier}"
    r = get_r(url)
    if not r:
        return pd.DataFrame()

    data = r.json().get("entries", [])
    if not data:
        print(f"❌ {tier.title()} 데이터 없음")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["tier"] = tier.title()
    df = df.sort_values("leaguePoints", ascending=False).reset_index(drop=True)
    return df

# =========================================
# 티어별 + RiotName 매핑 통합
# =========================================
def get_all_tiers_with_riotnames(limit_per_tier=10):
    all_df = pd.DataFrame()
    tiers = ["challenger", "grandmaster", "master"]

    for tier in tiers:
        df = get_tft_tier_data(tier)
        if df.empty:
            continue

        df = df.head(limit_per_tier)
        df["riotName"] = None

        for i, row in df.iterrows():
            puuid = row.get("puuid")
            name = get_riot_name_by_puuid(puuid)
            df.at[i, "riotName"] = name or "Unknown"
            print(f"[{tier.title()}] {i+1}/{len(df)} → {name}")
            time.sleep(1.2)

        all_df = pd.concat([all_df, df])

    # 저장
    now = dt.datetime.now().strftime("%Y%m%d")
    os.makedirs("data/all_tiers", exist_ok=True)
    save_path = f"data/all_tiers/{now}_tft_alltiers.csv"
    all_df.to_csv(save_path, index=False, encoding="utf-8-sig")
    print(f"\n✅ 전체 티어 저장 완료: {save_path}")
    return all_df

# =========================================
# 예쁜 출력 (tabulate)
# =========================================
def display_tier_table(df):
    if df.empty:
        print("❌ 데이터가 없습니다.")
        return

    # 인덱스 1부터
    df = df.copy()
    df.reset_index(drop=True, inplace=True)
    df.index = df.index + 1

    # 승률 계산
    if "wins" in df.columns and "losses" in df.columns:
        df["winRate(%)"] = (df["wins"] / (df["wins"] + df["losses"]) * 100).round(1)

    # 필요한 컬럼만 정리
    cols = [c for c in ["tier", "riotName", "leaguePoints", "wins", "losses", "winRate(%)"] if c in df.columns]
    table = df[cols].rename(columns={
        "tier": "티어",
        "riotName": "🎯 Riot ID",
        "leaguePoints": "🏆 LP",
        "wins": "✅ 승",
        "losses": "❌ 패",
        "winRate(%)": "📊 승률(%)" 
    })

    # 출력
    print("\n=== TFT 전체 티어 순위표 ===")
    print(tabulate(table, headers="keys", tablefmt="fancy_grid", showindex=True))

# =========================================
# 실행
# =========================================
if __name__ == "__main__":
    result = get_all_tiers_with_riotnames(limit_per_tier=10)
    display_tier_table(result)
