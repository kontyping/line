import os
import requests
import feedparser

# ==========================================
# 1. 設定と環境変数
# ==========================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# サイトを追加（4Gamer, ファミ通, AUTOMATON + Gamer, 電撃オンライン）
RSS_URLS = [
    "https://www.4gamer.net/rss/index.xml",
    "https://www.famitsu.com/rss/fcom-all.xml",
    "https://automaton-media.com/feed/",
    "https://www.gamer.ne.jp/rss/gamer.xml",
    "https://dengekionline.com/rss/all.xml"
]

# 英語名や略称も含めたキーワード網羅リスト
KEYWORDS = [
    # にゃんこ大戦争
    "にゃんこ大戦争", "にゃんこ", "The Battle Cats",
    # まどドラ / マギアエクセドラ
    "まどドラ", "マギアエクセドラ", "Magia Exedra", "魔法少女まどか☆マギカ Magia Exedra",
    # ブルーアーカイブ
    "ブルアカ", "ブルーアーカイブ", "Blue Archive",
    "新作", "ゲーム"
]

SENT_URLS_FILE = "sent_urls.txt"
MAX_NOTIFY_COUNT = 3  # 1回の通知で送る最大記事数

# ==========================================
# 2. 関数定義
# ==========================================
def load_sent_urls():
    if os.path.exists(SENT_URLS_FILE):
        with open(SENT_URLS_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_url(url):
    with open(SENT_URLS_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def summarize_with_groq(title, link):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    prompt = f"以下のゲーム記事をゲーマー向けに分かりやすく、箇条書きで3行に要約してください。\n\nタイトル: {title}\nURL: {link}"
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "あなたは最新のゲーム情報を分かりやすく伝える優秀なキュレーターBotです。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 256
    }
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Groq API Error for {title}: {e}")
        return "要約の取得に失敗しました。"

def send_line_message(text):
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        response = requests.post("https://api.line.me/v2/bot/message/push", headers=headers, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"LINE API Error: {e}")

# ==========================================
# 3. メイン処理
# ==========================================
def main():
    sent_urls = load_sent_urls()
    candidate_articles = []

    # 各RSSからキーワードが含まれる未送信の記事を収集
    for rss_url in RSS_URLS:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            
            # タイトルまたは概要にキーワードが含まれているか判定
            if any(keyword.lower() in title.lower() for keyword in KEYWORDS):
                if link not in sent_urls:
                    candidate_articles.append({"title": title, "link": link})

    if not candidate_articles:
        print("未通知の対象記事はありませんでした。")
        return

    # 未通知の記事の中から最大 MAX_NOTIFY_COUNT 件まで抽出して処理
    target_articles = candidate_articles[:MAX_NOTIFY_COUNT]

    for article in target_articles:
        print(f"Processing: {article['title']}")
        summary = summarize_with_groq(article['title'], article['link'])
        
        message = f"🎮 【ゲーム情報】\n{article['title']}\n\n{summary}\n\n🔗 {article['link']}"
        
        send_line_message(message)
        save_sent_url(article['link'])
        print(f"Sent & Saved: {article['link']}")

if __name__ == "__main__":
    main()
