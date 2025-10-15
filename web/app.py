from flask import Flask, render_template, request, jsonify

import os

# 📁 현재 파일 위치 기준으로 static / templates 절대경로 지정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_url_path='/static',  # ✅ Flask가 /static/... URL을 인식하도록
    static_folder=os.path.join(BASE_DIR, 'static'),
    template_folder=os.path.join(BASE_DIR, 'templates')
)

# 🎬 인트로 페이지
@app.route('/')
def index():
    return render_template('index.html')

# 💬 챗봇 페이지
@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

# 🧠 여기 추가! (JS에서 POST하는 엔드포인트)
@app.route('/api/chat', methods=['POST'])
def api_chat():
    user_msg = request.json.get("message", "")
    reply = f"'{user_msg}'에 대한 덱 추천 기능은 준비 중이에요!"
    return jsonify({"reply": reply})

if __name__ == '__main__':
    print("📂 static folder:", app.static_folder)
    print("📂 template folder:", app.template_folder)
    app.run(debug=True)



# # 🧠 챌린저 300명 API
# @app.route('/api/challenger300', methods=['GET'])
# def get_challenger_data():
#     df = get_tiers_with_riotnames(tiers=["challenger"], limit_per_tier=300)
#     return jsonify(df.to_dict(orient="records"))

# # 🗣️ 챗봇 응답 API
# @app.route('/api/chat', methods=['POST'])
# def chat_response():
#     user_msg = request.json.get("message")
#     response = f"'{user_msg}'에 대한 덱 추천 기능은 준비 중이에요!"
#     return jsonify({"reply": response})

# if __name__ == '__main__':
#     app.run(debug=True)
