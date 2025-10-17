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
ROOT_DIR = os.path.dirname(BASE_DIR)  # ✅ 프로젝트 루트 경로
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)  # ✅ riot 폴더 인식 가능하게 추가

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

# 🔹 Riot 전적검색 모듈 불러오기
try:
    from riot.tft_matches_fetch import get_match_summary_by_name
    print("✅ tft_matches_fetch 모듈 로드 완료!")
except ImportError as e:
    print("⚠️ riot/tft_matches_fetch.py 파일을 찾을 수 없습니다. 전적검색 기능은 비활성화됩니다.", e)
    get_match_summary_by_name = None


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

    # ✅ [추가] 전적검색 기능
    # ✅ "전적" 키워드나 "#"이 포함된 경우 전적검색으로 인식
    if "#" in user_msg or any(k in user_msg for k in ["전적검색", "전적", "티어", "랭크"]):
        if get_match_summary_by_name is None:
            return jsonify({"reply": "⚠️ 전적검색 모듈이 없습니다. riot/tft_matches_fetch.py를 확인해주세요."})
        riot_id = (
            user_msg.replace("전적검색", "")
            .replace("전적", "")
            .replace("검색", "")
            .replace("티어", "")
            .replace("랭크", "")
            .strip()
        )
        if len(riot_id) < 3:
            return jsonify({"reply": "❌ 소환사명을 정확히 입력해주세요. 예: Hide on bush#KR1"})
        result = get_match_summary_by_name(riot_id)
        return jsonify({"reply": result})

    # ✅ 이하 기존 로직 100% 유지

    positive_words = [
        "응", "ㅇㅇ", "웅", "엉", "어", "그래", "좋아", "해줘",
        "알려줘", "그거", "보여줘", "오키", "ㅇㅋ", "ㅇ", "ㅋ"
    ]
    curse_words = ["시발", "씨발", "ㅅㅂ", "개새", "fuck", "shit"]
    nonsense_patterns = [
        "ㅋㅋ", "ㅎㅎ", "ㅠㅠ", "ㅜㅜ", "ㅁㄴ", "ㅇㄹ", "ㄷㄷ", "??", "ㄴㄴ", "ㅇㅇㅇ", "ㅗ",
        "배고파", "점심", "밥", "날씨", "공부", "사랑", "연애", "게임 추천"
    ]

    # -------------------------------
    # ⚠️ 욕설 필터링
    # -------------------------------
    if any(c in user_msg for c in curse_words):
        session.clear()
        return jsonify({"reply": "⚠️ 부적절한 표현은 삼가주세요.\n롤토체스 관련 질문만 부탁드려요!"})

    # -------------------------------
    # ❌ 의미 없는 입력 차단
    # -------------------------------
    if (
        len(user_msg) < 1
        or re.fullmatch(r"[a-zA-Z0-9ㄱ-ㅎㅏ-ㅣ]+", user_msg)
        or (any(p in user_msg for p in nonsense_patterns) and user_msg not in positive_words)
    ):
        session.clear()
        return jsonify({"reply": "무슨 말씀이신지 잘 모르겠어요 😅\n롤토체스 관련 질문만 해주세요!"})

    # ==================================================
    # 🧠 복수 챔피언 & 메타 질문 인식 (GPT)
    # ==================================================
    mentioned = []
    for champ, data in champion_data.items():
        for kw in data["keywords"]:
            if re.search(rf"{re.escape(kw.lower())}", user_msg):
                mentioned.append(champ)
                break
    mentioned = list(set(mentioned))

    meta_triggers = ["요즘", "메타", "최근", "지금", "핫한", "추천해줘", "덱 추천", "덱 뭐가 좋아"]

    # ✅ 여러 챔피언이 동시에 언급된 경우
    if len(mentioned) >= 2 and any(k in user_msg for k in ["덱", "조합", "시너지", "가야", "가면", "추천", "무슨 덱", "무슨 조합"]):
        try:
            prompt = f"""
                너는 롤토체스(TFT) 전략 전문가이자 코치야.
                유저가 말한 챔피언들: {mentioned}
                아래는 각 챔피언의 덱 데이터야:
                {json.dumps({c: champion_data[c].get("deck", []) for c in mentioned}, ensure_ascii=False, indent=2)}
                여러 명의 챔피언을 유저가 말했을 경우에, 공통으로 쓸 수 있는 덱(시너지)이 있는지 분석하고 그 덱을 추천해줘.
                이 챔피언들이 공통으로 사용할 수 있는 덱이 있다면 하나 추천해줘.
                공통 덱이 전혀 없으면 “공통 덱이 없어요 😅 다른 덱을 가는 게 좋아보여요.”라고 대답해줘.

                답변 형식:
                📘 [덱 이름] 덱 추천!
                ⭐ 핵심 챔피언: ...
                🧩 보조 챔피언: ...
                ⚙️ 시너지: ...
                💡 덱 설명: ...
                """
            gpt_reply = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "너는 롤토체스 챔피언 조합 전문가야."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
            )
            reply = gpt_reply.choices[0].message.content.strip()
            session["last_bot_msg"] = reply
            session["last_intent"] = "deck"
            session["last_champ"] = ", ".join(mentioned)
            return jsonify({"reply": reply})

        except Exception as e:
            print("❌ GPT 복수 챔피언 처리 오류:", e)
            pass

    # ✅ “요즘 메타 뭐야?” 같은 모호 질문
    if any(k in user_msg for k in meta_triggers) and any(k in user_msg for k in ["덱", "추천", "시너지"]):
        try:
            prompt2 = """
                        너는 현재 TFT 메타를 잘 아는 전략가야.
                        현재 시즌 기준으로 강력한 덱 3가지를 아래 형식으로 추천해줘.

                        📘 [덱 이름] 덱 추천해 드릴게요!
                        ⭐ 핵심 챔피언: ...
                        🧩 보조 챔피언: ...
                        ⚙️ 시너지: ...
                        💡 덱 설명: ...
                        """
            gpt2 = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "너는 TFT 최신 메타 분석가야."},
                    {"role": "user", "content": prompt2}
                ],
                temperature=0.7,
            )
            reply2 = gpt2.choices[0].message.content.strip()
            session["last_bot_msg"] = reply2
            session["last_intent"] = "deck"
            return jsonify({"reply": reply2})

        except Exception as e:
            print("❌ GPT 메타 질문 오류:", e)
            pass

    # ==================================================
    # ✅ 나머지 기존 로직 (단일 챔피언)
    # ==================================================
    detected_champ = None
    for champ, data in champion_data.items():
        for keyword in data["keywords"]:
            if re.search(rf"(^|[^가-힣a-zA-Z0-9]){re.escape(keyword.lower())}([^가-힣a-zA-Z0-9]|$)", user_msg):
                detected_champ = champ
                break
        if detected_champ:
            break

    # ✅ 긍정 응답 처리
    if user_msg in positive_words:
        last_champ = session.get("last_champ")
        last_intent = session.get("last_intent")

        if last_champ and last_intent == "deck":
            items_data = champion_data.get(last_champ, {}).get("items", [])
            if items_data:
                pick = random.sample(items_data, k=min(3, len(items_data)))
                reply = f"{last_champ}의 추천 아이템은 {', '.join(pick)} 입니다!"
                session["last_bot_msg"] = reply
                session["last_intent"] = "items"
                return jsonify({"reply": reply})
            else:
                return jsonify({"reply": f"{last_champ}의 아이템 정보가 없어요 😅"})

        return jsonify({"reply": "이전에 챔피언을 언급하지 않으셨어요 😅\n예: '잔나 덱 추천'처럼 말해주세요!"})

    # ✅ 챔피언 없으면 기본 안내
    if not detected_champ:
        return jsonify({"reply": "현재 시즌 데이터에는 없는 챔피언이에요 😅\n다른 챔피언으로 시도해보세요!"})

    session["last_champ"] = detected_champ
    info = champion_data[detected_champ]

    # ==================================================
    # 🔹 덱 추천 / 아이템 추천 / 설명
    # ==================================================
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

    elif "템" in user_msg or "아이템" in user_msg:
        items_data = info.get("items", [])
        if items_data:
            pick = random.sample(items_data, k=min(3, len(items_data)))
            reply = f"{detected_champ}의 추천 아이템은 {', '.join(pick)} 입니다!"
        else:
            reply = "아이템 정보가 없어요 😅"
        session["last_bot_msg"] = reply
        session["last_intent"] = "items"
        return jsonify({"reply": reply})

    reply = f"{detected_champ} 챔피언 설명 💫\n{info.get('description', '설명 정보가 없어요.')}"
    session["last_bot_msg"] = reply
    session["last_intent"] = "description"
    return jsonify({"reply": reply})


# 🚀 실행
if __name__ == "__main__":
    app.run(debug=True)
