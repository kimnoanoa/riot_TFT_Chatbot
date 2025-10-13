import json

with open("data/ko_kr.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(data.keys())
