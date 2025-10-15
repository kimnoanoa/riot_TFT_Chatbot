import json
import random

# TFT 데이터 로드 (champions.json, items.json, traits.json, augments.json 같은 구조)
with open("data/champions.json", "r", encoding="utf-8") as f:
    champions = json.load(f)

with open("data/items.json", "r", encoding="utf-8") as f:
    items = json.load(f)

with open("data/synergy_traits.json", "r", encoding="utf-8") as f:
    traits = json.load(f)

with open("data/augments.json", "r", encoding="utf-8") as f:
    augments = json.load(f)

dataset = []

# 질문 템플릿 패턴
champion_templates = [
    "{name} 뭐함?",
    "{name} 특성 알려줘",
    "{name} 시너지 뭐야?",
    "{name} 조합 어떻게 가?",
    "{name} 덱 뭐에 써?",
    "{name} 코스트 얼마임?",
    "{name} 능력이 뭐야?",
]

item_templates = [
    "{name} 효과 뭐야?",
    "{name} 무슨 아이템임?",
    "{name} 만들려면 뭐필요함?",
    "{name} 재료 알려줘",
    "{name} 코어아이템 맞음?",
]

trait_templates = [
    "{name} 시너지 설명해줘",
    "{name} 효과 뭐야?",
    "{name} 시너지 쓰임새",
    "{name} 덱 어디에 씀?",
]

augment_templates = [
    "{name} 증강 뭐임?",
    "{name} 효과 알려줘",
    "{name} 언제 골라?",
    "{name} 발동 효과",
]

# 데이터 생성 함수
def make_entry(user_text, bot_text):
    return {"user": user_text, "bot": bot_text}

# 챔피언 데이터 생성
for champ in champions:
    for t in random.sample(champion_templates, 5):  # 다양화를 위해 랜덤 샘플
        user_q = t.format(name=champ["name"])
        bot_a = f"{champ['name']}는 {champ['cost']}코스트 챔피언이며 {', '.join(champ['traits'])} 특성을 가지고 있고, 스킬은 '{champ['ability']['name']} - {champ['ability']['desc']}'입니다."
        dataset.append(make_entry(user_q, bot_a))

# 아이템 데이터
for item in items:
    for t in random.sample(item_templates, 5):
        user_q = t.format(name=item["name"])
        bot_a = f"{item['name']}은(는) '{item['desc']}' 효과가 있으며, 재료는 {item['from']}입니다."
        dataset.append(make_entry(user_q, bot_a))

# 시너지 데이터
for trait in traits:
    for t in random.sample(trait_templates, 4):
        user_q = t.format(name=trait["name"])
        bot_a = f"{trait['name']} 시너지는 '{trait['desc']}' 효과를 제공합니다."
        dataset.append(make_entry(user_q, bot_a))

# 증강 데이터
for aug in augments:
    for t in random.sample(augment_templates, 4):
        user_q = t.format(name=aug["name"])
        bot_a = f"{aug['name']} [{aug['tier']}] 증강은 '{aug['desc']}' 효과를 가지고 있습니다."
        dataset.append(make_entry(user_q, bot_a))

# 최소 500개 보장 + 셔플
random.shuffle(dataset)
dataset = dataset[:600]  # 600개 확보 후 절단

# JSONL 저장
with open("tft_dataset.jsonl", "w", encoding="utf-8") as f:
    for row in dataset:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

print("✅ 생성 완료: tft_dataset.jsonl (총", len(dataset), "문장)")
