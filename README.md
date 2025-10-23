# 🎮 Riot TFT Chatbot  
> **롤토체스(TFT)** 데이터를 활용한 AI 챗봇 & 시너지 시뮬레이터 프로젝트
> https://riot-tft-chatbot.onrender.com/chatbot

---

## 🧠 프로젝트 개요  
이 프로젝트는 **Riot Games의 Teamfight Tactics (TFT)** 데이터를 기반으로  
**덱 추천 / 시너지 예측 / 전적 분석 / 챔피언 정보 제공** 등을 수행하는  
**AI 챗봇 및 시뮬레이터형 웹 애플리케이션**입니다.  

사용자는 단순히 “요네 나왔는데 어떤 덱 가야 돼?” 같은 질문을 입력하면,  
챗봇이 데이터 분석과 GPT 모델을 통해 **최적의 조합과 아이템**을 추천합니다.

---

## 🧩 주요 기능  

| 기능 | 설명 |
|------|------|
| 💬 **TFT 챗봇 대화** | 챔피언, 시너지, 아이템 관련 질문에 자연어로 응답 |
| 🔍 **덱/시너지 추천** | 선택된 챔피언 기반으로 승률 높은 조합 예측 |
| ⚔️ **전적 조회** | Riot API를 통한 소환사 정보 및 경기 기록 확인 |
| 🧮 **시너지 시뮬레이터** | 드래그 앤 드롭으로 챔피언 배치 후 시너지 확인 |
| 🧠 **데이터 기반 학습 구조** | ko_kr.json 기반 전처리 및 AI 분석 로직 포함 |
| 🌐 **웹 UI 제공** | Flask + HTML/CSS/JS 기반 인터랙티브 UI |

---

## 🛠️ 기술 스택  

### 🔹 Backend
- **Python / Flask** – 서버 및 API 처리
- **OpenAI GPT API** – 자연어 질의 응답
- **Riot Games API** – 실시간 소환사 및 매치 데이터 조회
- **dotenv / requests / json** – API 호출 및 환경변수 관리  

### 🔹 Frontend
- **HTML5 / CSS3 / JavaScript**
- **Drag & Drop** 기반 챔피언 보드 구현
- **YouTube 영상 배경 + 별빛 애니메이션 효과**
- **시너지 예측 시뮬레이터 페이지**

### 🔹 Data & AI
- **ko_kr.json** – TFT 공식 데이터 세트 (챔피언/아이템/시너지)
- **전처리 스크립트**: `riot_api.py`, `tft_recommender.py`
- **학습용 데이터셋**: `tft_dataset.jsonl`
- **OpenAI API** – 자연어 기반 추천 모델 연동

---

## 📊 모델 학습 및 데이터 처리 설명  

### 1️⃣ 데이터 수집  
- **Riot API** 및 **ko_kr.json** 파일을 통해 최신 TFT 챔피언, 특성, 아이템 데이터를 수집  
- `riot/riot_api.py`를 사용해 **챌린저/마스터급 유저 전적**을 일부 샘플링  

### 2️⃣ 전처리  
- **중복 / 불필요 필드 제거**  
- **챔피언 이름 / 특성 / 시너지 키워드 한글화 매핑**  
- **아이템 및 증강체 데이터 병합**

### 3️⃣ 모델 학습 개념  
- 단순 통계 기반이 아닌 **“질문 → 의도 파악 → 조합 추천”** 패턴 학습  
- OpenAI GPT API를 통해 **자연어 → 챔피언/시너지 매핑 응답** 구현  
- 향후 로컬 모델 학습 시 JSON 데이터 기반 **의사결정 트리 / 추천 모델** 적용 가능

### 4️⃣ 예시 코드 스니펫
```python
from openai import OpenAI
import json

client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

with open("data/ko_kr.json", "r", encoding="utf-8") as f:
    data = json.load(f)

question = "요네 나왔는데 무슨 덱 가야 돼?"
response = client.responses.create(
    model="gpt-4o-mini",
    input=f"질문: {question}\n참고 데이터: {data['setData'][:2]}"
)
print(response.output_text)

