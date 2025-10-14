# 챌린저 조회하는 파일

import requests
import datetime as dt
import time
import os
import pandas as pd

pd.set_option('display.max_columns', None)      # 열 모두 표시
pd.set_option('display.max_rows', None)         # 행 모두 표시
pd.set_option('display.width', 200)             # 한 줄 최대 너비
pd.set_option('display.max_colwidth', 300)       # 컬럼 최대 너비

api_key = "RGAPI-9163dd26-25e7-4d1b-a419-2f8582d8ec2c"
x = dt.datetime.now()
now_csv = x.strftime("%Y%m%d")
now = x.strftime("%Y/%m/%d %H:%M:%S")

# 요청 헤더
request_header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",  # 기본 브라우저 UA
    "Accept": "application/json",                               # JSON 응답 수락
    "Accept-Language": "en-US,en;q=0.9",                        # 한글 대신 ASCII만
    "Accept-Encoding": "gzip, deflate, br",                     # 서버 응답 압축 허용
    "Connection": "keep-alive",                                 # 지속 연결
    "Origin": "https://developer.riotgames.com",                # Riot 개발자 도메인
    "Cache-Control": "no-cache",                                # 캐싱 방지
    "X-Riot-Token": api_key                                     # 인증 키
}


# 안정적 API 요청 함수
def get_r(url):
    while True:
        try:
            r = requests.get(url, headers=request_header, timeout=5)
            r.raise_for_status()  # HTTPError 발생 시 예외 처리
            return r
        except requests.exceptions.HTTPError as http_err:
            if r.status_code == 429:  # 호출 제한
                print("429 Rate limit exceeded, 10초 대기...")
                time.sleep(10)
                continue
            elif r.status_code == 403:  # API 키 만료
                print("403 Forbidden - API 키 만료 가능")
                return None
            elif r.status_code in [502, 503]:  # 서버 오류
                print(f"{r.status_code} 서버 오류, 5초 대기 후 재시도...")
                time.sleep(5)
                continue
            else:
                print(f"HTTP error: {r.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"연결 오류: {e}, 5초 대기 후 재시도...")
            time.sleep(5)
            continue

# Challenger 티어 데이터 가져오기
def league_v1_get_challenger():
    print("Start - Get Challenger Data")
    
    # CSV 폴더 확인
    csv_folder = "data/challenger"
    if not os.path.exists(csv_folder):
        os.makedirs(csv_folder)

    csv_file = f"{csv_folder}/{now_csv}_challenger.csv"
    
    # CSV 이미 존재하면 읽기
    if os.path.isfile(csv_file):
        try:
            challenger_df = pd.read_csv(csv_file, index_col=0)
            print(f"CSV 로드 완료: {csv_file}")
            return challenger_df
        except Exception as e:
            print(f"CSV 로드 실패: {e}, 새로 API 호출")
    
    # API 호출
    url = "https://kr.api.riotgames.com/tft/league/v1/challenger"
    r = get_r(url)
    if r is None:
        print("API 호출 실패")
        return pd.DataFrame()  # 빈 DataFrame 반환

    try:
        rjson = r.json()
        entries = rjson.get("entries", [])
        if not entries:
            print("No challenger entries found")
            return pd.DataFrame()
        
        df = pd.DataFrame(entries)
        # 불필요 컬럼 제거 및 정렬
        drop_cols = ["wins", "rank", "losses", "veteran", "inactive", "hotStreak", "freshBlood"]
        df = df.drop(columns=[c for c in drop_cols if c in df.columns])
        df = df.sort_values("leaguePoints", ascending=False).reset_index(drop=True)
        
        # CSV 저장
        df.to_csv(csv_file)
        print(f"Challenger 데이터 저장 완료: {csv_file}")
        return df

    except Exception as e:
        print(f"데이터 처리 실패: {e}")
        return pd.DataFrame()
    
if __name__ == "__main__":
    challenger_df = league_v1_get_challenger()
    if not challenger_df.empty:
        print(challenger_df.head(20))  # 상위 5개 데이터 확인
    else:
        print("데이터가 없습니다.")
        

        
def challenger_data():
    data = league_v1_get_challenger()
    # add name, puuid가 아직 안되어있는 데이터다
    summ_data = data.copy().set_index("summonerName")
    if os.path.isfile("data/challenger.json"):
        challenger_hx_df = pd.read_json("data/challenger.json", orient="index")
        idx1 = summ_data.index
        idx2 = challenger_hx_df.index
        idx3 = idx1.difference(idx2)
        new_df = summ_data.loc[idx3].copy()
        new_df["summonerName"] = new_df.index
        # 그중에 data->summdata로 여기서 new_df를 추출후 다시 add name과, puuid 추가
        # ( index를 summnerName으로 바꾼상태라 다시 reset 후 함수)
        new_df.reset_index(drop=True, inplace=True)
        new_add_df = add_name_puuid(new_df).set_index("summonerName")
        final_df = pd.concat([challenger_hx_df, new_add_df])
    else:
        challenger_hx_df = data
        new_data = add_name_puuid(challenger_hx_df)
        final_df = new_data
        final_df.set_index("summonerName", inplace=True)
    final_df.to_json("data/challenger.json", orient="index", force_ascii=False)
    idx4 = final_df.index
    idx5 = summ_data.index
    data = final_df.loc[idx4.isin(idx5)]
    return data

def add_name_puuid(df):
    print("start - add name and puuid")
    print(df)
    start = time.time()
    df2 = df.copy()

    for i, Id in enumerate(df2["summonerId"]):
        try:
            summonerId_data = summoner_v1_get_summoner_new_name_puuid(Id)
            new_name = summonerId_data[0]
            puuid = summonerId_data[1]
            df2.loc[i, "newName"] = new_name
            df2.loc[i, "puuid"] = puuid
            print(f"success new_name,puuid - location : {i}")

        except Exception as e:
            print(f"error - location : {i, Id}")
            print(e)
            pass
    end = time.time()
    print(f"success - c_df2 (add name, puuid): {end - start:.2f} sec")
    return df2

def summoner_v1_get_summoner_new_name_puuid(SummonerId):

    url = f"https://kr.api.riotgames.com/tft/summoner/v1/summoners/{SummonerId}"
    r = get_r(url)

    if r.status_code == 200:
        pass

    elif r.status_code == 429 or r.status_code == 502:
        if r.status_code == 429:
            print("api cost full : infinite loop start")
        elif r.status_code == 502:
            print(" 502 error : infinite loop start")
        start_time = time.time()
        i = 1
        while True:
            if r.status_code == 429 or r.status_code == 502:
                print(f"try 10 seconds wait time: {i}  loops")
                time.sleep(10)
                i = i + 1
                r = get_r(url)

            elif r.status_code == 200:
                print("total wait time :", time.time() - start_time)
                break
    else:
        print(r.status_code)

    rJson = r.json()
    new_name = rJson["name"]
    puuid = rJson["puuid"]

    return new_name, puuid

