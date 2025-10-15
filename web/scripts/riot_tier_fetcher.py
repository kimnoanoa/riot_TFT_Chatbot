import os
import time
import requests
import pandas as pd
import datetime as dt
from dotenv import load_dotenv

# 🌿 .env 파일 로드
load_dotenv()

API_KEY = os.getenv("RIOT_API_KEY")
if not API_KEY:
    raise ValueError("⚠️ 환경 변수에서 RIOT_API_KEY를 찾을 수 없습니다. .env 파일을 확인하세요.")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-Riot-Token": API_KEY,
}

# 안정적 요청
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

# TFT 티어 데이터
def get_tft_tier_data(tier):
    url = f"https://kr.api.riotgames.com/tft/league/v1/{tier}"
    r = get_r(url)
    if not r:
        return pd.DataFrame()
    data = r.json().get("entries", [])
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data)
    df["tier"] = tier.title()
    df = df.sort_values("leaguePoints", ascending=False).reset_index(drop=True)
    return df

# PUUID로 RiotName 매핑
def get_riot_name_by_puuid(puuid, region="asia"):
    if not puuid or len(puuid) < 30:
        return None
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    r = get_r(url)
    if not r:
        return None
    data = r.json()
    name = data.get("gameName")
    tag = data.get("tagLine")
    return f"{name}#{tag}" if name and tag else name

# 티어별 데이터 + RiotName 매핑
def get_tiers_with_riotnames(tiers=["challenger"], limit_per_tier=300):
    all_df = pd.DataFrame()
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
    os.makedirs("data/tft_tiers", exist_ok=True)
    save_path = f"data/tft_tiers/{dt.datetime.now().strftime('%Y%m%d')}_{'_'.join(tiers)}.csv"
    all_df.to_csv(save_path, index=False, encoding="utf-8-sig")
    print(f"✅ 저장 완료: {save_path}")
    return all_df
