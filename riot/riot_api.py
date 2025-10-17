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

if not API_KEY:
    raise ValueError("⚠️ 환경 변수에서 RIOT_API_KEY를 찾을 수 없습니다. .env 파일을 확인하세요.")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "X-Riot-Token": API_KEY,
}

# 🕓 현재 날짜/시간
x = dt.datetime.now()
now_csv = x.strftime("%Y%m%d")
now = x.strftime("%Y/%m/%d %H:%M:%S")

# =====================================================
# 공통 요청 함수
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
# Riot Account API로 닉네임 조회
# =====================================================
def get_riot_name_by_puuid(puuid, region="asia"):
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

    # ✅ 티어 정보 추가
    tier = data.get("tier", "CHALLENGER")
    df["tier"] = tier

    print(f"✅ 상위 {len(df)}명 불러옴 (티어: {tier})")
    return df

# =====================================================
# TFT puuid → Riot 닉네임 매핑
# =====================================================
def get_riot_names_from_tft_challengers(limit=30):
    print("🚀 롤체 챌린저 → Riot 닉네임 매핑 시작")
    df = get_tft_challenger(limit)
    if df.empty:
        print("❌ 챌린저 데이터 없음")
        return pd.DataFrame()

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
        time.sleep(1.2)

    now = dt.datetime.now().strftime("%Y%m%d")
    save_path = f"data/challenger/{now}_tft_to_riot_top{limit}.csv"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    df.to_csv(save_path, index=False, encoding="utf-8-sig")
    print(f"✅ 결과 저장 완료: {save_path}")
    return df

# =====================================================
# 실행
# =====================================================
if __name__ == "__main__":
    result = get_riot_names_from_tft_challengers(limit=30)
    if not result.empty:
        print("\n=== 🌟 TFT 챌린저 순위표 ===")

        cols = [c for c in ["tier", "riotName", "leaguePoints", "wins", "losses"] if c in result.columns]
        table = result[cols].copy()
        table.reset_index(drop=True, inplace=True)
        table.index = table.index + 1

        if "wins" in table.columns and "losses" in table.columns:
            table["winRate(%)"] = (table["wins"] / (table["wins"] + table["losses"]) * 100).round(1)

        # 컬럼 이름 바꾸기
        table.rename(columns={
            "tier": "💎 티어",
            "riotName": "🎯 Riot ID",
            "leaguePoints": "🏆 LP",
            "wins": "✅ 승",
            "losses": "❌ 패",
            "winRate(%)": "📊 승률(%)"
        }, inplace=True)

        # 숫자 오른쪽 정렬, 문자열 중앙 정렬
        table_styles = {
            "💎 티어": str.center,
            "🎯 Riot ID": str.center,
            "🏆 LP": lambda x: f"{x:>5}",
            "✅ 승": lambda x: f"{x:>5}",
            "❌ 패": lambda x: f"{x:>5}",
            "📊 승률(%)": lambda x: f"{x:>6}"
        }

        for col, align_func in table_styles.items():
            if col in table.columns:
                table[col] = table[col].apply(align_func)

        print(tabulate(table, headers="keys", tablefmt="fancy_grid", showindex=True, stralign="center", numalign="right"))

def get_challenger_rank_table(limit=10):
    """
    TFT 챌린저 순위표 (상위 limit명)를 실시간으로 불러와서
    균등 정렬된 문자열로 반환합니다.
    """
    df = get_tft_challenger(limit=limit)
    if df.empty:
        return "⚠️ 챌린저 데이터를 불러올 수 없습니다."

    # ✅ 승률 계산
    if "wins" in df.columns and "losses" in df.columns:
        df["winRate"] = (df["wins"] / (df["wins"] + df["losses"]) * 100).round(1)

    lines = ["📊 **TFT 챌린저 TOP {}** (실시간 기준)\n".format(limit)]

    for i, row in df.iterrows():
        puuid = row.get("puuid")
        riot_name = get_riot_name_by_puuid(puuid)
        name = riot_name if riot_name and riot_name != "Unknown" else row.get("summonerName", "Unknown")

        lp = row.get("leaguePoints", 0)
        wins = row.get("wins", 0)
        losses = row.get("losses", 0)
        winrate = f"{row.get('winRate', 0):.1f}%"

        # 🏅 순위 이모지 (1~10)
        rank_emoji = {
            1: "🥇", 2: "🥈", 3: "🥉",
            4: "4️⃣", 5: "5️⃣", 6: "6️⃣",
            7: "7️⃣", 8: "8️⃣", 9: "9️⃣", 10: "🔟"
        }.get(i + 1, f"{i+1}️⃣")

        # ✨ 깔끔한 고정폭 정렬 (승률은 항상 끝부분 정렬)
        line = (
            f"{rank_emoji} {name:<18} │ "
            f"LP: {lp:>4} │ "
            f"승: {wins:>3} │ "
            f"패: {losses:>3} │ "
            f"승률: {winrate:>6}"
        )
        lines.append(line)

        time.sleep(1.0)  # Riot API 호출 제한 보호

    # 📦 하나의 문자열로 합쳐서 반환
    return "\n".join(lines)

