import os
import time
import requests
import pandas as pd
import datetime as dt
from tabulate import tabulate
from dotenv import load_dotenv

# 🌿 .env 파일 로드
load_dotenv()

# 🔑 환경 변수에서 API 키 불러오기
API_KEY = os.getenv("RIOT_API_KEY")

# 🧩 예외 처리 (키가 없을 때 알림)
if not API_KEY:
    raise ValueError("⚠️ 환경 변수에서 RIOT_API_KEY를 찾을 수 없습니다. .env 파일을 확인하세요.")

# 🛠️ 요청 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-Riot-Token": API_KEY,
}

# 📅 현재 날짜 (파일명 등에서 사용)
NOW = dt.datetime.now().strftime("%Y%m%d")


# ---------------- 공통 요청 ----------------
def get_r(url):
    while True:
        try:
            r = requests.get(url, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                return r
            elif r.status_code == 429:
                print("⚠️ 429 Too Many Requests → 10초 대기")
                time.sleep(10)
                continue
            elif r.status_code in [502, 503]:
                print(f"⚠️ 서버 오류 {r.status_code} → 5초 대기")
                time.sleep(5)
                continue
            elif r.status_code in [403, 401]:
                print("❌ API 키 만료 or 인증 문제")
                return None
            else:
                print(f"❌ HTTP 오류 {r.status_code} - {url}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"🔁 연결 오류: {e}, 5초 후 재시도")
            time.sleep(5)

# ---------------- Riot ID 조회 ----------------
def get_riot_name_by_puuid(puuid):
    if not puuid or len(puuid) < 30:
        return None
    url = f"https://asia.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    r = get_r(url)
    if not r:
        return None
    data = r.json()
    game = data.get("gameName")
    tag = data.get("tagLine")
    return f"{game}#{tag}" if game and tag else game or "Unknown"

# ---------------- Summoner ID → name, puuid ----------------
def get_summoner_info(summoner_id):
    url = f"https://kr.api.riotgames.com/tft/summoner/v1/summoners/{summoner_id}"
    r = get_r(url)
    if not r:
        return None, None
    data = r.json()
    return data.get("name"), data.get("puuid")

# ---------------- 티어별 한 페이지 수집 ----------------
def get_tier_page_data(tier, division="I", page=1):
    if tier in ["CHALLENGER", "GRANDMASTER", "MASTER"]:
        url = f"https://kr.api.riotgames.com/tft/league/v1/{tier.lower()}"
    else:
        url = f"https://kr.api.riotgames.com/tft/league/v1/entries/{tier}/{division}?page={page}"

    r = get_r(url)
    if not r:
        return pd.DataFrame()

    data = r.json()
    entries = data["entries"] if isinstance(data, dict) and "entries" in data else data
    if not entries:
        return pd.DataFrame()

    df = pd.DataFrame(entries)
    df["tier"] = tier
    df["division"] = division
    return df

# ---------------- 이름/puuid/RiotID 추가 ----------------
def enrich_with_names(df, limit=5):
    df = df.head(limit).copy()
    df["summonerName"], df["puuid"], df["riotName"] = None, None, None

    for i, row in df.iterrows():
        sid = row.get("summonerId")
        if not sid:
            print(f"⚠️ summonerId 없음, 건너뜀 ({row})")
            continue

        name, puuid = get_summoner_info(sid)
        df.at[i, "summonerName"] = name
        df.at[i, "puuid"] = puuid

        riot = get_riot_name_by_puuid(puuid) if puuid else None
        df.at[i, "riotName"] = riot or "Unknown"
        print(f"[{row['tier']} {row['division']}] {i+1}/{len(df)} - {name} → {riot}")
        time.sleep(1.2)

    return df

# ---------------- 전체 티어 한 페이지 수집 ----------------
def collect_one_page_all_tiers(limit_per_tier=3):
    all_df = pd.DataFrame()
    normal_tiers = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND"]
    high_tiers = ["MASTER", "GRANDMASTER", "CHALLENGER"]

    for tier in normal_tiers:
        df = get_tier_page_data(tier, "I", 1)
        if not df.empty:
            enriched = enrich_with_names(df, limit_per_tier)
            all_df = pd.concat([all_df, enriched])

    for tier in high_tiers:
        df = get_tier_page_data(tier)
        if not df.empty:
            enriched = enrich_with_names(df, limit_per_tier)
            all_df = pd.concat([all_df, enriched])

    os.makedirs("data/all_tiers", exist_ok=True)
    save_path = f"data/all_tiers/{NOW}_tft_alltiers_page1.csv"
    all_df.to_csv(save_path, index=False, encoding="utf-8-sig")
    print(f"\n✅ 전체 티어 한 페이지 저장 완료: {save_path}")
    return all_df

# ---------------- 표 출력 ----------------
def display_tier_table(df):
    if df.empty:
        print("❌ 데이터가 없습니다.")
        return

    df.reset_index(drop=True, inplace=True)
    df.index = df.index + 1

    if "wins" in df.columns and "losses" in df.columns:
        df["winRate(%)"] = (df["wins"] / (df["wins"] + df["losses"]) * 100).round(1)

    cols = [c for c in ["tier", "division", "riotName", "leaguePoints", "wins", "losses", "winRate(%)"] if c in df.columns]
    table = df[cols].rename(columns={
        "tier": "티어",
        "division": "구간",
        "riotName": "🎯 Riot ID",
        "leaguePoints": "🏆 LP",
        "wins": "✅ 승",
        "losses": "❌ 패",
        "winRate(%)": "📊 승률(%)"
    })

    print("\n=== TFT 전체 티어 샘플 ===")
    print(tabulate(table, headers="keys", tablefmt="fancy_grid", showindex=True))

# ---------------- 실행 ----------------
if __name__ == "__main__":
    result = collect_one_page_all_tiers(limit_per_tier=3)
    display_tier_table(result)
