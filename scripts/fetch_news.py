import feedparser
import requests
import os
import re
from datetime import datetime

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

RSS_FEEDS = [
    "https://rsshub.app/36kr/newsflashes",
    "https://rsshub.app/jiqizhixin/posts",
    "https://rsshub.app/qbitai",
    "https://rsshub.app/huxiu/rss",
]

def fetch_all_news():
    all_articles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries[:10]:
                summary = ""
                if hasattr(entry, "summary") and entry.summary:
                    summary = entry.summary[:200]
                elif hasattr(entry, "description") and entry.description:
                    summary = entry.description[:200]
                all_articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": summary,
                })
                count += 1
            print(f"  ✅ 已获取 {count} 条：{url}")
        except Exception as e:
            print(f"  ❌ 失败 {url}: {e}")
    return all_articles

def summarize_with_deepseek(articles):
    if not articles:
        return "<p>今日暂无新闻数据。</p>"

    news_text = "\n".join([
        f"{i+1}. [{a['title']}]({a['link']}) — {a['summary']}"
        for i, a in enumerate(articles[:60])
    ])

    prompt = f"""你是一位专业的 AI 新闻编辑，请根据以下新闻列表，生成一份「AI 行业每日简报」。
要求：
1. 挑选 8-10 条最重要的新闻。
2. 分为「🔥 技术突破」「💰 商业动态」「📋 政策与行业」三个板块。
3. 每条新闻用 1-2 句话概括（不超过 60 字），并附上原文链接。
4. 顶部写一段 100 字以内的「今日热点速览」。
5. 输出严格 HTML 片段，不要包含 ```html``` 标记。
结构示例：
<p>【今日热点速览】...</p>
<h2>🔥 技术突破</h2>
<ul>
  <li><a href="链接">标题</a> - 摘要</li>
  ...
</ul>
...

新闻列表：
{news_text}
"""

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个严谨的 AI 新闻编辑，只输出 HTML 片段，不要额外说明。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2500
    }

    try:
        resp = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        raw_html = result["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"DeepSeek API 调用失败: {e}")
        return "<p class='error'>AI 生成简报失败，请检查 Actions 日志。</p>"

    # 清洗可能的 markdown 标记
    cleaned = re.sub(r'^```html\s*', '', raw_html, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*```$', '', cleaned)
    return cleaned.strip()

def build_html(summary_html):
    today = datetime.now().strftime("%Y年%m月%d日")
    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI 新闻简报 - {today}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 20px; }}
    .header h1 {{ margin: 0 0 10px 0; }}
    .header p {{ margin: 0; opacity: 0.9; }}
    .content {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
    .content h2 {{ color: #667eea; border-bottom: 2px solid #eee; padding-bottom: 8px; }}
    .content h3 {{ color: #764ba2; }}
    .content ul {{ padding-left: 20px; }}
    .content li {{ margin-bottom: 8px; line-height: 1.6; }}
    .content a {{ color: #667eea; text-decoration: none; }}
    .content a:hover {{ text-decoration: underline; }}
    .footer {{ text-align: center; margin-top: 20px; color: #999; font-size: 14px; }}
    .error {{ color: red; font-weight: bold; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>🤖 AI 行业每日简报</h1>
    <p>📅 {today} ｜ 基于 DeepSeek 自动生成 ｜ 每日 8:00 更新</p>
  </div>
  <div class="content">
    {summary_html}
  </div>
  <div class="footer">
    <p>🕒 最后更新：{update_time} (北京时间)</p>
    <p>新闻来源：36氪、机器之心、量子位、虎嗅 | <a href="https://github.com">GitHub</a> 托管</p>
  </div>
</body>
</html>"""

def main():
    print(f"🚀 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 启动新闻生成...")
    articles = fetch_all_news()
    print(f"📰 共获取 {len(articles)} 条新闻")

    if len(articles) == 0:
        error_html = "<p class='error'>今日未能获取到新闻，可能 RSSHub 暂时不可用，明日将自动重试。</p>"
        full_html = build_html(error_html)
    else:
        print("🧠 调用 DeepSeek 生成简报...")
        summary_html = summarize_with_deepseek(articles)
        print("🎨 构建完整页面...")
        full_html = build_html(summary_html)

    os.makedirs("docs", exist_ok=True)
    output_path = os.path.join("docs", "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)
    print(f"✅ 简报已保存至 {output_path}")

if __name__ == "__main__":
    main()
