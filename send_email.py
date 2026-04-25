import feedparser
import smtplib
import os
import sys
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timezone
import re

# ================== 配置区 ==================
RSS_FILE = 'rss_feeds.txt'
SMTP_SERVER = 'smtp.163.com'
SMTP_PORT = 465               # 隐式SSL，减少STARTTLS问题
TIMEOUT = 15                  # 连接超时
EMAIL_USER = os.environ.get('EMAIL_USER', '')
EMAIL_PASS = os.environ.get('EMAIL_PASS', '')
RECEIVER = os.environ.get('RECEIVER_EMAIL', '')
# ===========================================

def clean_html(raw_html):
    """移除HTML标签，截取前200字符"""
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()[:200]

def fetch_entries():
    entries = []
    if not os.path.exists(RSS_FILE):
        raise FileNotFoundError(f"RSS file {RSS_FILE} not found")

    with open(RSS_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print(f"Found {len(urls)} RSS sources")
    for url in urls:
        try:
            feed = feedparser.parse(url)
            # 只取最新2条
            for entry in feed.entries[:2]:
                title = entry.get('title', 'No title')
                link = entry.get('link', '')
                published = entry.get('published', '')
                summary = entry.get('summary', '')
                summary = clean_html(summary) if summary else ''
                source = feed.feed.get('title', url.split('/')[2])
                entries.append({
                    'title': title,
                    'link': link,
                    'published': published,
                    'summary': summary,
                    'source': source
                })
        except Exception as e:
            print(f"⚠️ Failed to fetch {url}: {e}")

    # 根据link去重
    seen = set()
    unique_entries = []
    for e in entries:
        if e['link'] not in seen:
            seen.add(e['link'])
            unique_entries.append(e)
    print(f"Collected {len(unique_entries)} unique articles")
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

    html = f"""<html>
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
    if not EMAIL_USER or not EMAIL_PASS or not RECEIVER:
        raise ValueError("Email credentials or receiver not set")

    msg = MIMEMultipart('alternative')
    msg['Subject'] = Header(f"每日AI算力&具身智能简报 - {datetime.now().strftime('%Y-%m-%d')}", 'utf-8')
    msg['From'] = EMAIL_USER
    msg['To'] = RECEIVER
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=TIMEOUT) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, RECEIVER, msg.as_string())
        print("✅ Email sent successfully")
    except smtplib.SMTPAuthenticationError:
        print("❌ Authentication failed — check EMAIL_USER and EMAIL_PASS (use authorization code, not login password)")
        raise
    except smtplib.SMTPConnectError:
        print(f"❌ Could not connect to {SMTP_SERVER}:{SMTP_PORT} — check network/firewall")
        raise
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        raise

if __name__ == '__main__':
    try:
        print("=== Script started ===")
        print(f"Python version: {sys.version}")
        print(f"Working directory: {os.getcwd()}")
        print(f"Files in directory: {os.listdir('.')}")

        # 检查环境变量
        for var in ('EMAIL_USER', 'EMAIL_PASS', 'RECEIVER_EMAIL'):
            if var not in os.environ:
                raise EnvironmentError(f"Missing environment variable: {var}")
        print("Environment variables OK")

        entries = fetch_entries()
        if entries:
            html = build_html(entries)
            send_email(html)
        else:
            print("⚠️ No entries found, email not sent.")
    except Exception as e:
        print(f"💥 Fatal error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
