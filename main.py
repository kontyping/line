import os
import requests
import feedparser
from datetime import datetime

# ==========================================
# 1. 設定と環境変数
# ==========================================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
LINE_ACCESS_TOKEN = os.environ.get("LINE_ACCESS_TOKEN")
LINE_USER_ID = os.environ.get("LINE_USER_ID")

# 巡回するRSSフィード（4Gamer, ファミ通, AUTOMATON）
RSS_URLS = [
    "https://www.4gamer.net/rss/index.xml",
    "https://www.famitsu.com/rss/fcom-all.xml",
    "https://automaton-media.com/feed/"
]

# 抽出対象のキーワード
KEYWORDS = ["にゃんこ大戦争", "まどドラ", "マギアエクセドラ", "ブルアカ", "ブルーアーカイブ"]
SENT_URLS_FILE = "sent_urls.txt"

# ==========================================
# 2. 関数定義
# ==========================================
def load_sent_urls():
    """送信済みのURLリストを読み込む"""
    if os.path.exists(SENT_URLS_FILE):
        with open(SENT_URLS_FILE, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_sent_url(url):
    """送信済みのURLを保存する"""
    with open(SENT_URLS_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def summarize_with_groq(title, link):
    """Groq APIを使用して記事を3行で要約する"""
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
    """LINE Messaging API経由でメッセージを送信する"""
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
    new_articles = []

    # RSSを巡回してキーワードに一致する新着記事を抽出
    for rss_url in RSS_URLS:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            title = entry.title
            link = entry.link
            
            # キーワードが含まれており、かつ未送信のURLのみ処理
            if any(keyword in title for keyword in KEYWORDS):
                if link not in sent_urls:
                    new_articles.append({"title": title, "link": link})

    if not new_articles:
        print("新しい通知対象の記事はありませんでした。")
        return

    # 新着記事を要約してLINEに通知
    for article in new_articles:
        print(f"Processing: {article['title']}")
        summary = summarize_with_groq(article['title'], article['link'])
        
        # LINEに送るメッセージの組み立て
        message = f"🎮 【ゲーム新着情報】\n{article['title']}\n\n{summary}\n\n🔗 {article['link']}"
        
        send_line_message(message)
        save_sent_url(article['link'])
        print(f"Sent & Saved: {article['link']}")

if __name__ == "__main__":
    main()
