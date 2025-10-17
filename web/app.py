from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from dotenv import load_dotenv
import json
import random
import os
import re
import sys

# 🌱 .env 로드
load_dotenv()

# 🔑 OpenAI API 키 확인
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ OPENAI_API_KEY가 .env에 설정되어 있지 않습니다!")

client = OpenAI(api_key=api_key)

# 📁 Flask 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

app = Flask(
    __name__,
    static_url_path="/static",
    static_folder=os.path.join(BASE_DIR, "static"),
    template_folder=os.path.join(BASE_DIR, "templates"),
)
app.secret_key = "noah_tft_secret"

# 🔹 챔피언 JSON 로드
DATA_PATH = os.path.join(BASE_DIR, "..", "data", "champion_data.json")
if not os.path.exists(DATA_PATH):
    print("⚠️ champion_data.json 파일을 찾을 수 없습니다:", DATA_PATH)
    champion_data = {}
else:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        champion_data = json.load(f)
    print(f"✅ {len(champion_data)}개의 챔피언 데이터 로드 완료!")

# 🔹 Riot 전적검색 모듈
try:
    from riot.tft_matches_fetch import get_match_summary_by_name
    print("✅ tft_matches_fetch 모듈 로드 완료!")
except ImportError as e:
    print("⚠️ riot/tft_matches_fetch.py 파일을 찾을 수 없습니다. 전적검색 기능 비활성화.", e)
    get_match_summary_by_name = None

# ✅ 초보자 덱 추천 모듈
try:
    from riot.beginner_deck_recommender import get_beginner_deck_recommendation
    print("✅ beginner_deck_recommender 모듈 로드 완료!")
except ImportError as e:
    print("⚠️ riot/beginner_deck_recommender.py 파일을 찾을 수 없습니다.", e)
    get_beginner_deck_recommendation = None

# ✅ 챌린저 순위표 모듈
try:
    from riot.riot_api import get_challenger_rank_table
    print("✅ riot_api 모듈 로드 완료!")
except ImportError as e:
    print("⚠️ riot/riot_api.py 파일을 찾을 수 없습니다.", e)
    get_challenger_rank_table = None

# ✅ TFT 챔피언 조합 추천 모듈 (새로 추가)
try:
    from riot.tft_recommender import process_user_query, recommend_champion_deck, recommend_meta_deck, CHALLENGER_DATA_GLOBAL
    print("✅ tft_recommender 모듈 로드 완료!")
except ImportError as e:
    print("⚠️ riot/tft_recommender.py 파일을 찾을 수 없습니다. 챔피언 조합 추천 기능 비활성화.", e)
    process_user_query = None
    recommend_champion_deck = None
    recommend_meta_deck = None
    CHALLENGER_DATA_GLOBAL = None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chatbot")
def chatbot():
    return render_template("chatbot.html")


# 💬 챗봇 API
@app.route("/api/chat", methods=["POST"])
def api_chat():
    user_msg = request.json.get("message", "").lower().strip()
    reply = ""

    # ================================================================
    # ✅ 1️⃣ 챔피언 복수 / 메타 질문 먼저 처리 (가장 우선순위 높음)
    # ================================================================
    if process_user_query and ("덱" in user_msg or "시너지" in user_msg or "메타" in user_msg):
        try:
            query_info = process_user_query(user_msg, CHALLENGER_DATA_GLOBAL)
            q_type = query_info["query_type"]

            # 2명 이상 챔피언이 언급된 경우 (조합 덱 추천)
            if q_type == "CHAMPION_QUERY" and len(query_info["champions"]) >= 2:
                reply = recommend_champion_deck(query_info["champions"])
                session["last_intent"] = "deck_combo"
                session["last_bot_msg"] = reply
                return jsonify({"reply": reply})

            # “메타” 관련 질문 (현재 챌린저 데이터 기반)
            elif q_type == "META_QUERY":
                reply = recommend_meta_deck(query_info["meta_data"])
                session["last_intent"] = "meta"
                session["last_bot_msg"] = reply
                return jsonify({"reply": reply})

        except Exception as e:
            print("⚠️ TFT 추천 모듈 처리 오류:", e)

    # ================================================================
    # ✅ 2️⃣ 일반 챔피언 관련 (단일 덱 / 아이템 / 설명)
    # ================================================================
    detected_champ = None
    for champ, data in champion_data.items():
        for keyword in data["keywords"]:
            if re.search(rf"(^|[^가-힣a-zA-Z0-9]){re.escape(keyword.lower())}([^가-힣a-zA-Z0-9]|$)", user_msg):
                detected_champ = champ
                break
        if detected_champ:
            break

    if detected_champ:
        session["last_champ"] = detected_champ
        info = champion_data[detected_champ]

        # ✅ 아이템 추천
        if "템" in user_msg or "아이템" in user_msg:
            items_data = info.get("items", [])
            if items_data:
                pick = random.sample(items_data, k=min(3, len(items_data)))
                reply = f"{detected_champ}의 추천 아이템은 {', '.join(pick)} 입니다!"
            else:
                reply = f"{detected_champ}의 아이템 정보가 없어요 😅"
            session["last_bot_msg"] = reply
            session["last_intent"] = "items"
            return jsonify({"reply": reply})

        # ✅ 덱 추천
        if "덱" in user_msg or "시너지" in user_msg or "추천" in user_msg:
            deck_data = info.get("deck", [])
            if deck_data:
                picked = random.choice(deck_data)
                core = ", ".join(picked.get("core", []))
                subs = ", ".join(picked.get("subs", []))
                synergy = ", ".join(picked.get("synergy", []))
                comment = picked.get("comment", "")
                reply = (
                    f"📘 {detected_champ} 덱 추천!\n\n"
                    f"⭐ 핵심 챔피언: {core}\n"
                    f"🧩 보조 챔피언: {subs}\n"
                    f"⚙️ 시너지: {synergy}\n\n"
                    f"💡 덱 설명: {comment}\n\n"
                    f"아이템 추천도 해드릴까요?"
                )
                session["last_bot_msg"] = reply
                session["last_intent"] = "deck"
                return jsonify({"reply": reply})

        # ✅ 기본 설명
        reply = f"{detected_champ} 챔피언 설명 💫\n{info.get('description', '설명 정보가 없어요.')}"
        session["last_bot_msg"] = reply
        session["last_intent"] = "description"
        return jsonify({"reply": reply})

    # ================================================================
    # ✅ 3️⃣ 기타 처리 (랭킹 / 초보자 / 긍정/부정 / 다른거 등)
    # ================================================================
    # ✅ 챌린저 순위 요청
    if any(k in user_msg for k in ["챌린저", "롤체 순위", "tft 순위", "랭킹", "순위표"]):
        if get_challenger_rank_table is None:
            return jsonify({"reply": "⚠️ riot_api.py 모듈이 없습니다. 챌린저 순위표 기능 비활성화."})
        try:
            result = get_challenger_rank_table()
            return jsonify({"reply": result})
        except Exception as e:
            print("❌ 챌린저 순위표 처리 오류:", e)
            return jsonify({"reply": "⚠️ 챌린저 순위 정보를 불러오는 중 오류가 발생했습니다."})

    # ✅ 초보자 덱 추천
    if any(k in user_msg for k in ["초보자", "입문자", "쉬운 덱", "시작", "beginner", "쉬운","좋아?"]):
        if get_beginner_deck_recommendation is None:
            return jsonify({"reply": "⚠️ beginner_deck_recommender.py 모듈이 없습니다."})
        try:
            result = get_beginner_deck_recommendation()
            session["last_bot_msg"] = result
            session["last_intent"] = "beginner"
            return jsonify({"reply": result})
        except Exception as e:
            print("❌ 초보자 덱 추천 오류:", e)
            return jsonify({"reply": "⚠️ 초보자 덱 추천 중 오류가 발생했습니다."})

    # ✅ 전적검색
    if "#" in user_msg or any(k in user_msg for k in ["전적검색", "전적", "티어"]):
        if get_match_summary_by_name is None:
            return jsonify({"reply": "⚠️ 전적검색 모듈이 없습니다."})
        riot_id = (
            user_msg.replace("전적검색", "")
            .replace("전적", "")
            .replace("검색", "")
            .replace("티어", "")
            .strip()
        )
        if len(riot_id) < 3:
            return jsonify({"reply": "❌ 소환사명을 정확히 입력해주세요. 예: Hide on bush#KR1"})
        result = get_match_summary_by_name(riot_id)
        return jsonify({"reply": result})

    # ✅ 긍정 / 부정 응답 추가 (덱 → 아이템 흐름)
    positive_words = ["응", "ㅇㅇ", "그래", "좋아", "웅", "엉", "ㅇㅋ", "오키", "해줘", "ㅇ"]
    negative_words = ["싫어", "아니", "ㄴ", "ㄴㄴ", "ㄴㅇ", "안 해", "안해", "그만", "별로", "아냐"]

    if any(word == user_msg or word in user_msg for word in positive_words):
        last_intent = session.get("last_intent")
        last_champ = session.get("last_champ")

        if last_intent == "deck" and last_champ:
            info = champion_data.get(last_champ, {})
            items_data = info.get("items", [])
            if items_data:
                pick = random.sample(items_data, k=min(3, len(items_data)))
                reply = f"💫 {last_champ}의 추천 아이템은 {', '.join(pick)} 입니다!"
            else:
                reply = f"{last_champ}의 아이템 정보가 없어요 😅"
            session["last_bot_msg"] = reply
            session["last_intent"] = "items"
            return jsonify({"reply": reply})

        elif last_intent == "beginner" and get_beginner_deck_recommendation:
            reply = get_beginner_deck_recommendation()
            session["last_bot_msg"] = reply
            return jsonify({"reply": reply})

        elif last_intent == "deck_combo" and recommend_meta_deck:
            reply = recommend_meta_deck(CHALLENGER_DATA_GLOBAL)
            session["last_bot_msg"] = reply
            session["last_intent"] = "meta"
            return jsonify({"reply": reply})

        return jsonify({"reply": "알겠어요 😊\n원하시는 덱이나 아이템을 말씀해주시면 도와드릴게요!"})

    if any(word == user_msg or word in user_msg for word in negative_words):
        return jsonify({"reply": "알겠습니다 😊\n원하실 때 다시 도와드릴게요!"})

    # -------------------------------------------------
    # 🔁 "다른거 / 또 추천" 처리
    # -------------------------------------------------
    alternate_words = [
        "다른거", "다른 거", "다른 덱", "다른 아이템", "다시 추천", "또", "바꿔줘",
        "하나 더", "랜덤으로", "더 보여줘", "또 추천해줘"
    ]
    if any(word in user_msg for word in alternate_words):
        last_intent = session.get("last_intent")
        last_champ = session.get("last_champ")

        # 🔹 초보자 덱
        if last_intent == "beginner" and get_beginner_deck_recommendation:
            last_reply = session.get("last_bot_msg", "")
            last_deck_name = None
            match = re.search(r"추천 덱: (.+?)\n", last_reply)
            if match:
                last_deck_name = match.group(1).strip()
            reply = get_beginner_deck_recommendation(last_deck_name)
            session["last_bot_msg"] = reply
            return jsonify({"reply": reply})

        # 🔹 아이템
        elif last_intent == "items" and last_champ:
            info = champion_data.get(last_champ, {})
            items_data = info.get("items", [])
            if items_data:
                pick = random.sample(items_data, k=min(3, len(items_data)))
                reply = f"🎲 {last_champ}의 또 다른 아이템 추천은 {', '.join(pick)} 입니다!"
                session["last_bot_msg"] = reply
                return jsonify({"reply": reply})

        # 🔹 덱
        elif last_intent == "deck" and last_champ:
            info = champion_data.get(last_champ, {})
            deck_data = info.get("deck", [])
            if deck_data:
                picked = random.choice(deck_data)
                core = ", ".join(picked.get("core", []))
                subs = ", ".join(picked.get("subs", []))
                synergy = ", ".join(picked.get("synergy", []))
                comment = picked.get("comment", "")
                reply = (
                    f"📘 {last_champ}의 또 다른 덱 추천!\n\n"
                    f"⭐ 핵심 챔피언: {core}\n"
                    f"🧩 보조 챔피언: {subs}\n"
                    f"⚙️ 시너지: {synergy}\n\n"
                    f"💡 덱 설명: {comment}\n"
                )
                session["last_bot_msg"] = reply
                return jsonify({"reply": reply})

        return jsonify({"reply": "무엇을 다시 추천해드릴까요? 😅"})


# 🚀 실행
if __name__ == "__main__":
    app.run(debug=True)
