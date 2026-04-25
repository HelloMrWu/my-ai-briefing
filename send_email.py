import feedparser
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
import time
import re

# 配置区
RSS_FILE = 'rss_feeds.txt'
SMTP_SERVER = 'smtp.qq.com'          # QQ邮箱，若用163则改为smtp.163.com
SMTP_PORT = 587
EMAIL_USER = os.environ['EMAIL_USER']   # GitHub Secret
EMAIL_PASS = os.environ['EMAIL_PASS']   # GitHub Secret
RECEIVER = os.environ['RECEIVER_EMAIL'] # GitHub Secret

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()

def fetch_entries():
    entries = []
    with open(RSS_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:  # 每个源取最新2条
                title = entry.get('title','No title')
                link = entry.get('link','')
                published = entry.get('published','')
                summary = entry.get('summary','')
                summary = clean_html(summary)[:200] if summary else ''
                source = feed.feed.get('title', url.split('/')[2])
                entries.append({
                    'title': title,
                    'link': link,
                    'published': published,
                    'summary': summary,
                    'source': source
                })
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
    # 去重（按link）
    seen = set()
    unique_entries = []
    for e in entries:
        if e['link'] not in seen:
            seen.add(e['link'])
            unique_entries.append(e)
    return unique_entries

def build_html(entries):
    now = datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d')
    items_html = ''
    for e in entries:
        pub = e['published'] if e['published'] else 'N/A'
        items_html += f"""
        <tr>
            <td style="padding:8px; border:1px solid #ddd;">
                <strong><a href="{e['link']}" style="color:#1a0dab; text-decoration:none;">{e['title']}</a></strong><br>
                <span style="color:#555; font-size:0.9em;">{e['source']} · {pub}</span><br>
                <span style="color:#333; font-size:0.9em;">{e['summary']}</span>
            </td>
        </tr>"""
    html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; margin:20px;">
            <h2 style="color:#2c3e50;">🤖 每日AI算力&具身智能简报 - {now}</h2>
            <p>共抓取 {len(entries)} 条最新动态，点击标题直接阅读原文。</p>
            <table style="border-collapse:collapse; width:100%;">
                {items_html}
            </table>
            <hr>
            <p style="font-size:0.8em; color:#888;">由 GitHub Actions 自动生成，每日定时推送。</p>
        </body>
    </html>"""
    return html

def send_email(html_content):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"每日AI算力&具身智能简报 - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'] = EMAIL_USER
    msg['To'] = RECEIVER
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, RECEIVER, msg.as_string())
        server.quit()
        print("Email sent successfully")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == '__main__':
    entries = fetch_entries()
    if entries:
        html = build_html(entries)
        send_email(html)
    else:
        print("No entries found, email not sent.")
