# riot/riot_api.py
import os
import requests
import time
from dotenv import load_dotenv

# =========================================================
# 🔹 1. 환경 변수 로드 (.env 강제 적용)
# =========================================================
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("RIOT_API_KEY="):
                os.environ["RIOT_API_KEY"] = line.strip().split("=", 1)[1]

load_dotenv(override=True)
RIOT_API_KEY = os.getenv("RIOT_API_KEY")

print(f"🔑 적용된 Riot API Key: {RIOT_API_KEY[:15]}...")


# =========================================================
# 🔹 2. 지역 라우팅 설정
# =========================================================
REGION_ROUTING = {
    "KR": "asia",
    "JP1": "asia",
    "NA1": "americas",
    "BR1": "americas",
    "OC1": "sea",
    "EUW1": "europe",
    "EUN1": "europe",
    "TR1": "europe",
    "RU": "europe",
}

HEADERS = {"X-Riot-Token": RIOT_API_KEY}


# =========================================================
# 🔹 3. 공통 요청 함수
# =========================================================
def request_api(url, params=None, retries=3, sleep_time=1):
    """API 요청 핸들러 (자동 재시도 및 rate limit 처리)"""
    for attempt in range(retries):
        res = requests.get(url, headers=HEADERS, params=params)

        if res.status_code == 200:
            return res.json()
        elif res.status_code == 401:
            print("❌ 401 Unauthorized — API 키가 잘못되었거나 만료되었습니다.")
            break
        elif res.status_code == 429:
            wait = int(res.headers.get("Retry-After", 2))
            print(f"⏳ Rate limit 발생 — {wait}s 대기 후 재시도...")
            time.sleep(wait)
        else:
            print(f"⚠️ 요청 실패 ({res.status_code}) → {url}")
            time.sleep(sleep_time)
    return None


# =========================================================
# 🔹 4. 소환사 정보 (지역 서버)
# =========================================================
def get_summoner_info(summoner_name: str, region="KR"):
    """소환사 이름으로 기본 정보(PUUID, ID 등) 가져오기"""
    # ✅ summoner는 지역 서버 (kr.api.riotgames.com) 로 요청해야 함
    url = f"https://{region.lower()}.api.riotgames.com/tft/summoner/v1/summoners/by-name/{summoner_name}"

    data = request_api(url)
    if not data:
        print("❌ 소환사 정보를 불러올 수 없습니다.")
        return None

    return {
        "name": data["name"],
        "level": data["summonerLevel"],
        "profileIconId": data["profileIconId"],
        "id": data["id"],
        "puuid": data["puuid"],
    }


# =========================================================
# 🔹 5. 전적 목록 (플랫폼 서버)
# =========================================================
def get_match_ids(puuid: str, region="KR", count=10):
    """플레이어의 최근 match_id 리스트 가져오기"""
    routing = REGION_ROUTING.get(region.upper(), "asia")
    url = f"https://{routing}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
    params = {"count": count}
    match_ids = request_api(url, params=params)
    if not match_ids:
        print("⚠️ 전적 ID를 불러올 수 없습니다.")
        return []
    return match_ids


# =========================================================
# 🔹 6. 개별 경기 상세 (플랫폼 서버)
# =========================================================
def get_match_detail(match_id: str, region="KR"):
    """match_id로 세부 경기 정보 가져오기"""
    routing = REGION_ROUTING.get(region.upper(), "asia")
    url = f"https://{routing}.api.riotgames.com/tft/match/v1/matches/{match_id}"
    data = request_api(url)
    if not data:
        print(f"⚠️ {match_id} 상세 정보를 불러올 수 없습니다.")
        return None
    return data


# =========================================================
# 🔹 7. 랭크 정보 (지역 서버)
# =========================================================
def get_rank_info(summoner_id: str, region="KR"):
    """소환사 ID 기준 랭크 정보 가져오기"""
    url = f"https://{region.lower()}.api.riotgames.com/tft/league/v1/entries/by-summoner/{summoner_id}"
    ranks = request_api(url)
    if not ranks:
        print("⚠️ 랭크 정보 없음")
        return []
    return [
        {
            "tier": r["tier"],
            "rank": r["rank"],
            "lp": r["leaguePoints"],
            "wins": r["wins"],
            "losses": r["losses"],
        }
        for r in ranks
    ]


# =========================================================
# 🔹 8. 최신 TFT 데이터 다운로드
# =========================================================
def get_tft_data():
    """최신 세트 데이터(ko_kr.json) 다운로드"""
    url = "https://raw.communitydragon.org/latest/cdragon/tft/ko_kr.json"
    print("📦 최신 TFT 데이터 다운로드 중...")
    res = requests.get(url)
    if res.status_code == 200:
        os.makedirs("data", exist_ok=True)
        with open("data/ko_kr.json", "wb") as f:
            f.write(res.content)
        print("✅ 최신 TFT 데이터 다운로드 완료 (data/ko_kr.json)")
        return True
    else:
        print("❌ 데이터 다운로드 실패:", res.status_code)
        return False


# =========================================================
# 🔹 9. 플레이어 요약
# =========================================================
def get_player_summary(summoner_name: str, region="KR"):
    """소환사명 → 랭크 + 최근 전적 + 첫 경기 요약"""
    info = get_summoner_info(summoner_name, region)
    if not info:
        return None

    ranks = get_rank_info(info["id"], region)
    matches = get_match_ids(info["puuid"], region, count=5)
    first_game = get_match_detail(matches[0], region) if matches else None

    summary = {
        "summoner": info,
        "rank": ranks[0] if ranks else {},
        "recent_match_ids": matches,
        "latest_match": first_game,
    }
    return summary


# =========================================================
# 🔹 10. 테스트 실행
# =========================================================
if __name__ == "__main__":
    summoner_name = "상만전"  # 테스트용 이름
    region = "KR"

    player = get_player_summary(summoner_name, region)
    if player:
        print("\n🎯 요약 결과:")
        print(f"이름: {player['summoner']['name']}")
        print(f"레벨: {player['summoner']['level']}")
        print(f"랭크: {player['rank'].get('tier', 'UNRANKED')} {player['rank'].get('rank', '')}")
        print(f"최근 전적 수: {len(player['recent_match_ids'])}")
