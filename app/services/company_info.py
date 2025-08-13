import google.generativeai as genai
from datetime import datetime
import feedparser
import requests
from urllib.parse import quote_plus
from app.config import GOOGLE_API_KEY, SERPAPI_KEY

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

def get_company_info(company_name: str) -> str:
    current_date = datetime.now()
    start_of_year_dt = datetime(current_date.year, 1, 1)
    start_date = start_of_year_dt.strftime('%Y-%m-%d')
    end_date = current_date.strftime('%Y-%m-%d')

    recent_headlines = []
    snapshot_lines = []
    key_people_lines = []

    # SERPAPI news & knowledge graph
    if SERPAPI_KEY:
        try:
            params = {
                "engine": "google_news",
                "q": company_name,
                "when": "365d",
                "api_key": SERPAPI_KEY,
                "hl": "en",
                "gl": "us",
            }
            resp = requests.get("https://serpapi.com/search.json", params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("news_results", [])[:8]:
                    title = item.get("title")
                    link = item.get("link")
                    date = item.get("date") or item.get("published_date") or ""
                    if title and link:
                        recent_headlines.append(f"- {date}: {title} ({link})")
        except Exception:
            pass

        try:
            params = {
                "engine": "google",
                "q": f"{company_name} company",
                "api_key": SERPAPI_KEY,
                "num": "10",
                "hl": "en",
                "gl": "us",
            }
            resp = requests.get("https://serpapi.com/search.json", params=params, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                kg = data.get("knowledge_graph", {}) or {}
                if kg:
                    if kg.get("title"):
                        snapshot_lines.append(f"- Full name: {kg['title']}")
                    if kg.get("description"):
                        snapshot_lines.append(f"- Description: {kg['description']}")
                    if kg.get("headquarters") or kg.get("headquarters_location"):
                        snapshot_lines.append(f"- HQ Location: {kg.get('headquarters') or kg.get('headquarters_location')}")
                    if kg.get("employees"):
                        snapshot_lines.append(f"- Size: {kg['employees']}")
                    if kg.get("CEO") or kg.get("ceo"):
                        key_people_lines.append(f"- CEO: {kg.get('CEO') or kg.get('ceo')}")
                    if kg.get("Founders") or kg.get("founders"):
                        key_people_lines.append(f"- Founders: {kg.get('Founders') or kg.get('founders')}")
        except Exception:
            pass

    # Fallback to RSS feeds
    if not recent_headlines:
        try:
            def fetch_query_headlines(q: str):
                query = quote_plus(q)
                rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
                return feedparser.parse(rss_url)

            feeds = [
                fetch_query_headlines(f'"{company_name}" when:365d'),
                fetch_query_headlines(f'"{company_name}" site:newsroom.{company_name.lower()}.com when:365d'),
                fetch_query_headlines(f'"{company_name}" site:investor.{company_name.lower()}.com when:365d'),
                fetch_query_headlines(f'"{company_name}" (site:reuters.com OR site:bloomberg.com OR site:cnbc.com OR site:wsj.com) when:365d')
            ]

            seen_titles = set()
            start_of_year = start_of_year_dt
            for feed in feeds:
                for entry in getattr(feed, 'entries', [])[:10]:
                    title = getattr(entry, 'title', '')
                    link = getattr(entry, 'link', '')
                    published_dt = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        try:
                            published_dt = datetime(*entry.published_parsed[:6])
                        except Exception:
                            continue
                    if published_dt and published_dt < start_of_year:
                        continue
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    published_str = getattr(entry, 'published', '')
                    recent_headlines.append(f"- {published_str}: {title} ({link})")
            recent_headlines = recent_headlines[:5]
        except Exception:
            pass

    headlines_block = "\n".join(recent_headlines) if recent_headlines else "- No external headlines fetched."
    snapshot_block = "\n".join(snapshot_lines) if snapshot_lines else "- No snapshot enrichment."
    key_people_block = "\n".join(key_people_lines) if key_people_lines else "- No key people enrichment."
    finance_block = ""

    prompt = f"""
You are a business research assistant preparing a person for an upcoming meeting with {company_name}.
As of {end_date}, use only information from the current year to date (from {start_date} to {end_date}). If no reliable updates are found in this window, say: "No YTD updates."
Retrieve the latest and most relevant information from credible sources.
Present it in a concise, scannable format that can be read in under 45 seconds.
Use short bullet points under the following sections:

1. Company Snapshot
{snapshot_block}

2. Recent Updates (YTD)
{headlines_block}

3. Key People (must always be populated)
{key_people_block}

4. Business Health (YTD, concise)
{finance_block}
"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"
