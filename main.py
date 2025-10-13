from riot.riot_api import get_summoner_info, get_match_detail
from riot.recommender import recommend_team, recommend_items, recommend_augment
from riot.analyzer import analyze_player


def chatbot(query):
    if "전적" in query:
        # ex: "페이커 전적 보여줘"
        name = query.replace("전적", "").strip()
        info = get_summoner_info(name)
        if not info:
            return f"'{name}' 소환사를 찾을 수 없어요."
        return analyze_player(info["puuid"])

    elif "템" in query:
        # ex: "요네 템 추천"
        champ = query.replace("템", "").replace("추천", "").strip()
        return recommend_items(champ)

    elif "덱" in query:
        # ex: "별수호자 덱 추천"
        keyword = query.replace("덱", "").replace("추천", "").strip()
        return recommend_team(keyword)

    elif "증강" in query:
        # ex: "멘토 증강 나오면 뭐가 좋아?"
        aug = query.replace("증강", "").strip()
        return recommend_augment(aug)

    else:
        return "덱, 템, 증강, 전적 중 하나를 물어봐주세요!"

if __name__ == "__main__":
    while True:
        q = input("💬 질문 > ")
        if q.lower() in ["exit", "quit"]:
            break
        print("🤖", chatbot(q))
