import smtplib
import os
import time
import hashlib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
import feedparser
from deep_translator import GoogleTranslator

# ==========================================
# 配置区域（请根据你的实际情况修改）
# ==========================================
RSS_SOURCES = [
    "https://feeds.feedburner.com/TheHackersNews",
    "https://blog.google/threat-analysis-group/rss/",
    # 继续添加你订阅的 RSS 源地址
]

KEYWORDS = []  # 留空则不过滤，也可填入关键词列表做过滤
MAX_ARTICLES_PER_SOURCE = 3  # 每个源最多保留几篇
DAYS_BACK = 1  # 只取最近多少天内的文章

# SMTP 配置（从 GitHub Secrets 读取）
EMAIL_HOST = "smtp.163.com"
EMAIL_PORT = 465
EMAIL_USER = os.environ["EMAIL_USER"]
EMAIL_PASS = os.environ["EMAIL_PASS"]
RECEIVER = os.environ["RECEIVER_EMAIL"]

# ==========================================
# 工具函数：RSS 解析与文章去重
# ==========================================
def parse_all_feeds(sources):
    all_articles = []
    seen = set()
    cutoff = datetime.now() - timedelta(days=DAYS_BACK)

    for url in sources:
        try:
            feed = feedparser.parse(url)
            source_title = feed.feed.get("title", url)
            count = 0
            for entry in feed.entries:
                # 获取发布时间
                published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
                if published_parsed:
                    pub_time = datetime.fromtimestamp(time.mktime(published_parsed))
                    if pub_time < cutoff:
                        continue
                else:
                    # 没有时间就保留
                    pub_time = datetime.now()

                # 去重（基于链接或标题）
                dedup_key = entry.get("link") or entry.get("title")
                if dedup_key and dedup_key in seen:
                    continue
                if dedup_key:
                    seen.add(dedup_key)

                # 提取文本信息
                title = entry.get("title", "无标题")
                summary = entry.get("summary", "")
                # 简单去除 HTML 标签（可选，保留 HTML 也没问题）
                import re
                summary_clean = re.sub(r"<.*?>", "", summary)[:300]  # 摘要截取300字符

                article = {
                    "title": title,
                    "summary": summary_clean,
                    "link": entry.get("link", ""),
                    "source": source_title,
                    "published": pub_time.strftime("%Y-%m-%d %H:%M"),
                }
                all_articles.append(article)
                count += 1
                if count >= MAX_ARTICLES_PER_SOURCE:
                    break
        except Exception as e:
            print(f"解析 {url} 失败: {e}")

    # 按发布时间倒序
    all_articles.sort(key=lambda x: x["published"], reverse=True)
    return all_articles

# ==========================================
# 翻译模块
# ==========================================
def translate_batch(texts, source='en', target='zh-CN'):
    try:
        if not texts:
            return []
        filtered = [t for t in texts if t and isinstance(t, str) and t.strip()]
        if not filtered:
            return texts
        translator = GoogleTranslator(source=source, target=target)
        translated = translator.translate_batch(filtered)
        # 重建结果，保持空文本的原文
        result = []
        idx = 0
        for original in texts:
            if original and isinstance(original, str) and original.strip():
                result.append(translated[idx])
                idx += 1
            else:
                result.append(original)
        return result
    except Exception as e:
        print(f"翻译失败: {e}")
        return texts

def translate_articles(articles):
    if not articles:
        return articles
    titles = [a.get("title", "") for a in articles]
    summaries = [a.get("summary", "") for a in articles]
    titles_zh = translate_batch(titles)
    summaries_zh = translate_batch(summaries)
    for i, a in enumerate(articles):
        a["title_zh"] = titles_zh[i] if i < len(titles_zh) else a["title"]
        a["summary_zh"] = summaries_zh[i] if i < len(summaries_zh) else a["summary"]
    return articles

# ==========================================
# 邮件发送
# ==========================================
def send_email(articles):
    # 使用 Jinja2 渲染模板
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("email_template.html")
    html = template.render(articles=articles)

    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"] = f"📰 每日安全资讯（中文） - {datetime.now().strftime('%Y-%m-%d')}"
    msg["From"] = EMAIL_USER
    msg["To"] = RECEIVER

    with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASS)
        smtp.send_message(msg)
    print("邮件发送成功")

# ==========================================
# 主流程
# ==========================================
if __name__ == "__main__":
    print("开始解析 RSS…")
    articles = parse_all_feeds(RSS_SOURCES)
    print(f"共获取 {len(articles)} 篇文章，开始翻译…")
    articles = translate_articles(articles)
    print("翻译完成，发送邮件…")
    send_email(articles)
    print("任务结束")
