import requests
import time
import os
import pandas as pd
import datetime as dt

load_dotenv()

API_KEY = os.getenv("RIOT_API_KEY")
if not API_KEY:
    print("❌ .env 파일에서 RIOT_API_KEY를 불러올 수 없습니다.")
    exit()

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Riot-Token": API_KEY
}


NOW = dt.datetime.now().strftime("%Y%m%d")

# ===========================================
# 공통 요청 함수
# ===========================================
def get_r(url):
    while True:
        try:
            r = requests.get(url, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                return r
            elif r.status_code == 429:
                print("⚠️ 429 - 요청 제한. 10초 대기...")
                time.sleep(10)
                continue
            elif r.status_code in [502, 503]:
                print(f"⚠️ 서버 오류 {r.status_code} → 재시도")
                time.sleep(5)
                continue
            else:
                print(f"❌ {r.status_code}: {url}")
                return None
        except requests.exceptions.RequestException:
            print("🔁 연결 오류 → 5초 후 재시도")
            time.sleep(5)

# ===========================================
# 티어 데이터 (챌린저, 그마, 마스터)
# ===========================================
def get_tier_data(tier):
    print(f"\n▶ {tier.title()} 데이터 수집 중...")
    url = f"https://kr.api.riotgames.com/tft/league/v1/{tier}"
    r = get_r(url)
    if not r:
        return pd.DataFrame()

    data = r.json().get("entries", [])
    if not data:
        print(f"❌ {tier.title()} 데이터 없음")
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df = df.sort_values("leaguePoints", ascending=False).reset_index(drop=True)
    df["tier"] = tier.title()
    return df[["summonerId", "summonerName", "leaguePoints", "tier"]]

# ===========================================
# SummonerId → (소환사명, puuid)
# ===========================================
def get_summoner_info(summoner_id):
    url = f"https://kr.api.riotgames.com/tft/summoner/v1/summoners/{summoner_id}"
    r = get_r(url)
    if r and r.status_code == 200:
        j = r.json()
        return j.get("name"), j.get("puuid")
    return None, None

# ===========================================
# puuid → RiotID(gameName#tagLine)
# ===========================================
def get_riot_name(puuid):
    if not puuid:
        return None
    url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    r = get_r(url)
    if r and r.status_code == 200:
        j = r.json()
        game = j.get("gameName")
        tag = j.get("tagLine")
        if game and tag:
            return f"{game}#{tag}"
    return None

# ===========================================
# 이름 및 RiotName 보강
# ===========================================
def enrich_with_names(df, limit=5):
    df = df.head(limit).copy()
    df["summonerName"], df["puuid"], df["riotName"] = None, None, None

    for i, row in df.iterrows():
        sid = row.get("summonerId")
        if not sid:
            print(f"⚠️ summonerId 없음, 건너뜀 ({row})")
            continue

        # 🔹 TFT 소환사 정보 요청
        name, puuid = get_summoner_info(sid)
        df.at[i, "summonerName"] = name
        df.at[i, "puuid"] = puuid

        # 🔹 Riot ID 조회
        riot = get_riot_name_by_puuid(puuid) if puuid else None

        # 🔹 Riot ID 없으면 TFT 닉네임으로 대체
        if not riot or riot == "Unknown":
            riot = name if name else "Unknown"

        df.at[i, "riotName"] = riot

        print(f"[{row['tier']} {row['division']}] {i+1}/{len(df)} → {riot}")
        time.sleep(1.2)  # API rate limit 방지

    return df


# ===========================================
# 전체 티어 처리
# ===========================================
def collect_all_tiers(limit=5):
    all_df = pd.DataFrame()
    for tier in ["challenger", "grandmaster", "master"]:
        base_df = get_tier_data(tier).head(limit)
        enriched_df = enrich(base_df)
        all_df = pd.concat([all_df, enriched_df])

    os.makedirs("data/all_tiers", exist_ok=True)
    save_path = f"data/all_tiers/{NOW}_tft_alltiers_riotname.csv"
    all_df.to_csv(save_path, encoding="utf-8-sig", index=False)
    print(f"\n✅ 저장 완료: {save_path}")
    return all_df

# ===========================================
# 실행
# ===========================================
if __name__ == "__main__":
    result = collect_all_tiers(limit=3)
    print("\n=== 샘플 출력 ===")
    print(result[["tier", "summonerName", "riotName", "leaguePoints"]])
