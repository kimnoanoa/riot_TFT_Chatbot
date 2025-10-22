# 🎮 Riot TFT Chatbot  
> **롤토체스(TFT)** 데이터를 활용한 AI 챗봇 프로젝트  

---

## 🧠 프로젝트 개요  
이 프로젝트는 **Riot Games의 Teamfight Tactics (TFT)** 데이터를 기반으로  
**덱 추천 / 시너지 예측 / 전적 분석 / 챔피언 정보 제공** 등의 기능을 수행하는  
**AI 챗봇 및 시뮬레이터형 웹 애플리케이션**입니다.  

사용자는 단순한 질문(예: “요네 나왔는데 무슨 덱 가야 돼?”)을 입력하면  
챗봇이 실시간으로 데이터를 분석해 최적의 덱 방향과 아이템, 시너지를 추천합니다.

---

## 🧩 주요 기능  
| 기능 | 설명 |
|------|------|
| 💬 **TFT 챗봇 대화** | 챔피언, 시너지, 아이템 관련 질문에 답변 |
| 🔍 **덱/시너지 추천** | 입력된 챔피언 기반으로 승률 높은 조합 예측 |
| ⚔️ **전적 조회** | Riot API를 통해 소환사 정보 및 전적 분석 |
| 🧮 **시너지 시뮬레이터** | 챔피언을 드래그 앤 드롭으로 배치하여 시너지 확인 |
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
- **Drag & Drop UI** – 챔피언 보드 구현
- **유튜브 영상 배경 / 별빛 애니메이션 효과**
- **시너지 예측 시뮬레이터 페이지**

### 🔹 Data & AI
- **ko_kr.json** – TFT 공식 데이터 세트 (챔피언/아이템/시너지)
- **전처리 스크립트 (riot_api.py, tft_recommender.py 등)**
- **OpenAI API** – 자연어 기반 추천 응답

---

## 🧭 프로젝트 구조  
riot_TFT_Chatbot/
│
├── app.py # Flask 서버 진입점
├── .env # API 키 (Riot, OpenAI)
├── requirements.txt # 필요한 패키지 목록
│
├── data/
│ ├── ko_kr.json # TFT 한국어 데이터 (챔피언/아이템/시너지)
│ └── champion_data.json # 챔피언 상세 데이터
│
├── riot/
│ └── riot_api.py # Riot API 전적 조회 모듈
│
├── models/
│ └── tft_recommender.py # 덱/시너지 추천 로직
│
├── templates/
│ ├── index.html # 메인 페이지
│ ├── chatbot.html # 챗봇 인터페이스
│ └── synergy_analyze.html # 시너지 예측 시뮬레이터
│
├── static/
│ ├── css/
│ │ ├── chatbot.css
│ │ ├── synergy_analyze.css
│ │ └── style.css
│ └── images/
│ ├── icon.png
│ └── champions/
│
└── README.md 




