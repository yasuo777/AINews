import feedparser
import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
import time
from openai import OpenAI

# 配置部分
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY") # 从环境变量获取
OPENAI_BASE_URL = "https://api.openai.com/v1" # 如果用DeepSeek或其他，修改此处
MODEL_NAME = "gpt-3.5-turbo" # 或 deepseek-chat

# AI新闻源列表 (RSS)
RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/artificial-intelligence/index.xml",
    "https://arstechnica.com/tag/ai/feed/",
    # 你可以在这里添加更多源
]

client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

def get_og_image(url):
    """从网页meta标签中提取封面图"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        image = soup.find("meta", property="og:image")
        if image:
            return image["content"]
    except Exception as e:
        print(f"图片提取失败: {e}")
    return "https://via.placeholder.com/800x400?text=AI+News" # 默认图片

def generate_summary(text):
    """使用AI生成中文摘要"""
    if not text or len(text) < 50:
        return text
    
    try:
        prompt = f"请将以下新闻内容总结为一段简练的中文摘要（100字以内），语气专业：\n\n{text[:2000]}"
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"摘要生成失败: {e}")
        return text[:100] + "..."

def load_existing_data():
    if os.path.exists('news_data.json'):
        with open('news_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def main():
    existing_data = load_existing_data()
    existing_links = [item['link'] for item in existing_data]
    new_items = []

    print("开始抓取新闻...")
    
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:3]: # 每个源只取最新的3条，避免处理过多
            if entry.link in existing_links:
                continue
            
            print(f"处理新新闻: {entry.title}")
            
            # 1. 获取图片
            image_url = get_og_image(entry.link)
            
            # 2. 生成摘要 (优先使用RSS的summary，如果没有则用content)
            raw_text = BeautifulSoup(entry.get('summary', '') or entry.get('content', [{}])[0].get('value', ''), "html.parser").get_text()
            summary = generate_summary(raw_text)
            
            news_item = {
                'title': entry.title,
                'link': entry.link,
                'image': image_url,
                'summary': summary,
                'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                'timestamp': time.time()
            }
            new_items.append(news_item)
            existing_links.append(entry.link)

    if new_items:
        # 合并数据：新数据在前，旧数据在后，保留最近的100条
        all_data = new_items + existing_data
        all_data = all_data[:100] 
        
        with open('news_data.json', 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"成功更新 {len(new_items)} 条新闻！")
    else:
        print("暂无新新闻。")

if __name__ == "__main__":
    main()
