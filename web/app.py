from flask import Flask, render_template, request, jsonify, session
import openai 
from dotenv import load_dotenv
import json
import random
import os
import re
import sys

# 🌱 .env 로드
load_dotenv()

# 📁 Flask 설정 위쪽에 추가
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)


# 🔑 OpenAI API 키 확인
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ OPENAI_API_KEY가 .env에 설정되어 있지 않습니다!")

openai.api_key = api_key

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


@app.route("/synergy")
def synergy():
    return render_template("synergy_analyze.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    user_msg = request.json.get("message", "").lower().strip()
    reply = ""

        # -------------------------------------------------
    # 🌈 일반 대화 (인사, 감정, 일상 감정 케어 - 존댓말 버전)
    # -------------------------------------------------
    casual_keywords = [
        "안녕", "하이", "ㅎㅇ", "반가워",
        "피곤", "기분", "심심", "힘들어", 
        "좋아", "우울", "짜증", "행복", "불안", "지쳤어","힘들다","에휴"
    ]

    if any(k in user_msg for k in casual_keywords):
        try:
            # 💬 OpenAI GPT로 자연스러운 존댓말 일상 대화 생성 (구버전 호환)
            import openai
            openai.api_key = os.getenv("OPENAI_API_KEY")

            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "당신은 따뜻하고 다정한 AI 친구입니다. "
                            "사용자에게 존댓말로 대답하며, 공감과 배려가 느껴지게 말하세요. "
                            "너무 길지 않게 자연스럽고 부드러운 톤으로 답하세요. "
                            "격식 있는 문장보다는 따뜻한 말투를 사용하세요. "
                            "예: ‘괜찮으세요?’, ‘힘드시겠어요’, ‘오늘도 수고 많으셨어요!’"
                        ),
                    },
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=200,
                temperature=0.8,
            )

            reply = completion["choices"][0]["message"]["content"].strip()
            return jsonify({"reply": reply})

        except Exception as e:
            print("⚠️ 일상 대화 처리 오류:", e)
            fallback_replies = [
                "😊 안녕하세요! 오늘 기분은 어떠세요?",
                "☕ 너무 무리하지 마세요. 잠깐 쉬어가셔도 괜찮아요.",
                "🌈 오늘은 좋은 일들이 많이 생기길 바라요.",
                "😄 언제나 응원하고 있어요!",
                "💪 괜찮아요, 지금도 충분히 잘하고 계세요."
            ]
            return jsonify({"reply": random.choice(fallback_replies)})


    
  # ✅ 오피덱 / 사기덱 / 메타덱 질문 대응
    if any(k in user_msg for k in ["오피", "사기덱", "op", "요즘 오피", "메타덱","사기 덱","오피 덱","op덱","op 덱","개사기덱","메타 덱","메타","좋은 덱","좋은덱"]):
        op_decks = [
            {
                "name": "빌지워터 미스 포츈 덱",
                "core": "미스 포츈, 루시안, 세나, 노틸러스, 타릭",
                "synergy": "후반 캐리 + 탄탄한 앞라인",
                "comment": "빠르게 레벨을 올려 미스 포츈을 중심으로 후반을 지배하는 현재 최상위 메타 덱입니다."
            },
            {
                "name": "Fast 9 플릿 덱",
                "core": "루시안, 세나, 미스 포츈, 노틸러스, 갈리오",
                "synergy": "Fast 9 운영 + 후반 화력",
                "comment": "초반 체력 관리 후 9레벨에서 강력한 유닛으로 완성하는 고점 높은 메타 덱입니다."
            },
            {
                "name": "공허 카이사 덱",
                "core": "카이사, 말자하, 초가스, 에코",
                "synergy": "후반 캐리 + 광역 피해",
                "comment": "후반에 카이사를 중심으로 폭발적인 딜을 내는 성장형 메타 덱입니다."
            },
            {
                "name": "아이오니아 유나라 덱",
                "core": "유나라, 오공, 다이애나, 세라핀, 쉔",
                "synergy": "균형 잡힌 전투 + 지속력",
                "comment": "앞라인과 딜의 균형이 좋아 순방률이 높은 안정적인 메타 덱입니다."
            },
            {
                "name": "프렐요드 AD 캐리 덱",
                "core": "애쉬, 트린다미어, 세주아니, 볼리베어",
                "synergy": "강력한 앞라인 + AD 딜러",
                "comment": "단단한 탱커와 AD 캐리 조합으로 초중후반 모두 안정적인 덱입니다."
            }
        ]


        formatted = "🔥 요즘 메타 최상위 오피 덱 리스트 🔥\n\n"
        for d in op_decks:
            formatted += (
                f"🏆 {d['name']}\n"
                f"⭐ 핵심 챔피언: {d['core']}\n"
                f"⚙️ 시너지: {d['synergy']}\n"
                f"💬 특징: {d['comment']}\n\n"
            )
        reply = formatted
        session["last_intent"] = "meta_hot"
        session["last_bot_msg"] = reply
        return jsonify({"reply": reply})

    
    if "#" in user_msg:
        if get_match_summary_by_name is None:
            return jsonify({"reply": "⚠️ 전적검색 모듈이 없습니다."})
        result = get_match_summary_by_name(user_msg)
        return jsonify({"reply": result})

    # 🚫 비속어 / 욕설 필터링
    bad_words = ["시발", "씨발", "병신", "ㅅㅂ", "ㅂㅅ", "fuck", "shit", "개새", "존나", "꺼져", "죽어", "미친","ㅗ","ㅗㅗ"]
    if any(word in user_msg for word in bad_words):
        return jsonify({
            "reply": (
                "⚠️ 부적절한 표현이 감지되었습니다.<br>"
                "건전한 대화를 부탁드려요 😊"
            )
        })
    # ✅ 일상 대화 응답
    if any(k in user_msg for k in ["점심", "밥", "먹을까", "저녁", "식사", "배고파","점메추","저메추"]):
        lunch_menu = random.choice(["김치찌개", "초밥", "제육볶음", "떡볶이", "샐러드", "라멘", "비빔밥","된장찌개","순대국","카레","돈까스","김밥","덮밥","볶음밥","라면"])
        reply = f"🍱 오늘은 {lunch_menu} 어때요? 맛있게 드세요 😋"
        return jsonify({"reply": reply})


    # ================================================================
    # ✅ 1️⃣ 챔피언 복수 / 메타 질문 먼저 처리 (가장 우선순위 높음)
    # ================================================================
    if process_user_query and ("덱" in user_msg or "시너지" in user_msg or "메타" in user_msg or "조합" in user_msg):
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
    # ✅ 2️⃣ 시너지(특성) 이름 기반 덱 추천 (champion_data.json에서 자동 추출)
    # ================================================================
    all_traits = set()
    for champ_info in champion_data.values():
        deck_list = champ_info.get("deck", [])
        for deck in deck_list:
            for t in deck.get("synergy", []):
                all_traits.add(t.strip())

    normalized_user_msg = user_msg.replace(" ", "")
    detected_trait = None
    trait_map = {t: t.replace(" ", "") for t in all_traits}

    for trait, normalized_trait in trait_map.items():
        if re.search(rf"{re.escape(normalized_trait.lower())}(덱|추천|조합)?", normalized_user_msg):
            detected_trait = trait
            break

    if detected_trait:
        matched_champs = []
        for champ_name, champ_info in champion_data.items():
            for deck in champ_info.get("deck", []):
                synergies = [s.replace(" ", "") for s in deck.get("synergy", [])]
                if detected_trait.replace(" ", "") in synergies:
                    matched_champs.append(champ_name)
                    break  # 챔피언당 한 번만 추가

        if matched_champs:
            core = ", ".join(matched_champs[:3])
            subs = ", ".join(matched_champs[3:7]) if len(matched_champs) > 3 else "기타 보조 챔피언 다양"
            reply = (
                f"⚙️ '{detected_trait}' 시너지 기반 덱 추천!\n\n"
                f"⭐ 핵심 챔피언: {core}\n"
                f"🧩 보조 챔피언: {subs}\n\n"
                f"💡 '{detected_trait}' 시너지는 특정 조건에서 강력한 효과를 발휘해요.\n"
            )
        else:
            reply = f"'{detected_trait}' 시너지를 사용하는 챔피언 정보를 찾지 못했습니다 😅"

        session["last_trait"] = detected_trait
        session["last_bot_msg"] = reply
        session["last_intent"] = "trait"
        return jsonify({"reply": reply})


    # ================================================================
    # ✅ 3️⃣ 일반 챔피언 관련 (단일 덱 / 아이템 / 설명)
    # ================================================================
    detected_champ = None
    for champ, data in champion_data.items():
        for keyword in data["keywords"]:
            if re.search(rf"{re.escape(keyword.lower())}(덱|시너지|추천|조합)?", user_msg):
                detected_champ = champ
                break
        if detected_champ:
            break

    # ✅ 시너지 예측 시뮬레이터 이동 요청
    if "시너지" in user_msg and "예측" in user_msg and "시뮬레이터" in user_msg:
        reply = (
            "🔮 시너지 예측 시뮬레이터를 실행하시겠어요?\n"
            "<a href='/synergy' target='_blank' "
            "style='display:inline-block;margin-top:10px;padding:8px 14px;"
            "background:#3b82f6;color:white;border-radius:6px;text-decoration:none;'>"
            "➡️ 시너지 시뮬레이터 열기</a>"
        )
        return jsonify({"reply": reply})

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
            champs = [detected_champ] if detected_champ else []
            if champs:
                try:
                    from riot.tft_recommender import _recommend_core_deck
                    reply = _recommend_core_deck(champs)
                    reply = reply.replace("**", "").replace("-", "•").replace("\n", "<br>")
                    reply += "<br><br>💡 아이템도 추천해드릴까요?"
                    session["last_bot_msg"] = reply
                    session["last_intent"] = "deck"
                    return jsonify({"reply": reply})
                except Exception as e:
                    print("⚠️ _recommend_core_deck 실행 오류:", e)
                    return jsonify({"reply": "⚠️ 덱 추천 중 오류가 발생했습니다."})
            else:
                return jsonify({
                    "reply": (
                        "❌ 챔피언 이름을 인식하지 못했습니다.<br>"
                        "예: <code>요네 덱 추천</code> 또는 <code>세라핀 시너지 추천</code>처럼 입력해보세요!"
                    )
                })

        # ✅ 기본 설명
        reply = (
            f"{detected_champ} 챔피언 설명 💫<br>"
            f"{info.get('description', '설명 정보가 없어요.')}"
        )
        session["last_bot_msg"] = reply
        session["last_intent"] = "description"
        return jsonify({"reply": reply})

    # ================================================================
    # ✅ 4️⃣ 기타 처리 (랭킹 / 초보자 / 긍정/부정 / 다른거 등)
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
    if any(k in user_msg for k in ["초보자", "입문자", "쉬운 덱", "시작", "beginner", "쉬운", "좋아?","초보"]):
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
    positive_words = ["응", "ㅇㅇ", "그래", "좋아", "웅", "엉", "ㅇㅋ", "오키", "해줘", "ㅇ", "어", "ㅇㅇㅇ","추천"]
    negative_words = ["싫어", "아니", "ㄴ", "ㄴㄴ", "ㄴㅇ", "안 해", "안해", "그만", "별로", "아냐", "ㄴㄴㄴ"]

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

    # -------------------------------------------------
    # 🧩 기본 응답 (모든 조건에 해당하지 않는 경우)
    # -------------------------------------------------
    if not reply:
        return jsonify({
            "reply": (
                "🤔 무슨 뜻인지 잘 모르겠어요.<br>"
                "챔피언 이름이나 덱, 시너지 관련 질문을 해보세요!<br>"
                "예: <code>세라핀 덱 추천</code>, <code>요네 아이템</code>, "
                "<code>전적검색 hide on bush#KR1</code>"
            )
        })


# 🚀 실행
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
