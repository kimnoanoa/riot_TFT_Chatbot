import requests
import time
import os
import pandas as pd
import datetime as dt

# ⚙️ 최신 API 키 입력 (매일 갱신 필요)
API_KEY = "RGAPI-9163dd26-25e7-4d1b-a419-2f8582d8ec2c"

# 공통 헤더 설정
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-Riot-Token": API_KEY,
}

# =====================================================
# 공통 요청 함수 (안정적 호출)
# =====================================================
def get_r(url):
    while True:
        try:
            r = requests.get(url, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                return r
            elif r.status_code == 429:
                print("⚠️ 429: Rate limit exceeded → 10초 대기")
                time.sleep(10)
                continue
            elif r.status_code in [502, 503]:
                print(f"⚠️ 서버 오류 {r.status_code} → 5초 대기 후 재시도")
                time.sleep(5)
                continue
            elif r.status_code in [403, 401]:
                print("❌ 인증 오류 (API 키 만료 또는 권한 문제)")
                return None
            else:
                print(f"❌ HTTP {r.status_code} 오류 - {url}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"🔁 연결 오류: {e} → 5초 대기 후 재시도")
            time.sleep(5)

# =====================================================
# Riot Account API로 닉네임(gameName#tagLine) 조회
# =====================================================
def get_riot_name_by_puuid(puuid, region="asia"):
    """
    Riot 통합 계정 API 사용.
    LOL을 하지 않아도 Riot 계정 닉네임(gameName#tagLine)을 가져올 수 있음.
    """
    if not isinstance(puuid, str) or len(puuid) < 30:
        print(f"⚠️ 잘못된 puuid: {puuid}")
        return None

    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"
    r = get_r(url)
    if r is None:
        return None

    try:
        data = r.json()
        game_name = data.get("gameName")
        tag_line = data.get("tagLine")
        if game_name and tag_line:
            return f"{game_name}#{tag_line}"
        elif game_name:
            return game_name
        else:
            return "Unknown"
    except Exception as e:
        print(f"⚠️ JSON 파싱 실패: {e}")
        return None

# =====================================================
# TFT 챌린저 데이터 가져오기
# =====================================================
def get_tft_challenger(limit=30):
    """
    TFT 챌린저 API에서 상위 N명 데이터 가져옴.
    """
    url = "https://kr.api.riotgames.com/tft/league/v1/challenger"
    r = get_r(url)
    if r is None:
        print("❌ TFT 챌린저 API 호출 실패")
        return pd.DataFrame()

    data = r.json()
    entries = data.get("entries", [])
    if not entries:
        print("❌ 챌린저 데이터 없음")
        return pd.DataFrame()

    df = pd.DataFrame(entries)
    df = df.sort_values("leaguePoints", ascending=False).reset_index(drop=True)
    df = df.head(limit)
    print(f"✅ 상위 {len(df)}명 불러옴")
    return df

# =====================================================
# 메인 로직: TFT puuid → Riot 닉네임 매핑
# =====================================================
def get_riot_names_from_tft_challengers(limit=30):
    print("🚀 롤체 챌린저 → Riot 닉네임 매핑 시작")
    df = get_tft_challenger(limit)
    if df.empty:
        print("❌ 챌린저 데이터 없음")
        return pd.DataFrame()

    # 결과 컬럼 추가
    df["riotName"] = None

    for i, row in df.iterrows():
        puuid = row.get("puuid")
        print(f"[{i+1}/{len(df)}] {row.get('summonerName')} → Riot 닉네임 조회 중...")
        name = get_riot_name_by_puuid(puuid)
        if name and name != "Unknown":
            df.at[i, "riotName"] = name
            print(f"  ✅ {name}")
        else:
            df.at[i, "riotName"] = "Unknown"
            print("  ⚠️ 조회 실패 (Riot 계정 비공개 또는 에러)")
        time.sleep(1.2)  # rate limit 방지

    # 결과 저장
    now = dt.datetime.now().strftime("%Y%m%d")
    save_path = f"data/challenger/{now}_tft_to_riot_top{limit}.csv"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    df.to_csv(save_path, index=False, encoding="utf-8-sig")
    print(f"✅ 결과 저장 완료: {save_path}")
    return df

# =====================================================
# 실행
# =====================================================

from tabulate import tabulate


if __name__ == "__main__":
    result = get_riot_names_from_tft_challengers(limit=30)
    if not result.empty:
        print("\n=== TFT 챌린저 순위표 ===")

    cols = [c for c in ["riotName", "leaguePoints", "wins", "losses"] if c in result.columns]
    table = result[cols].copy()
    table.reset_index(drop=True, inplace=True)
    table.index = table.index + 1

    if "wins" in table.columns and "losses" in table.columns:
        table["winRate(%)"] = (table["wins"] / (table["wins"] + table["losses"]) * 100).round(1)

    table.rename(columns={
        "riotName": "🎯 Riot ID",
        "leaguePoints": "🏆 LP",
        "wins": "✅ 승",
        "losses": "❌ 패",
        "winRate(%)": "📊 승률(%)"
    }, inplace=True)

    # ✅ tabulate로 깔끔하게 출력
    print(tabulate(table, headers="keys", tablefmt="fancy_grid", showindex=True))


