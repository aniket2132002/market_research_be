import os
import re
import io
import contextlib
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime, timedelta
import feedparser
from urllib.parse import quote_plus
import yfinance as yf
import requests
import wikipedia
from app.config import GOOGLE_API_KEY, SERPAPI_KEY

# Load the API key from the .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Configure the Gemini API
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

    # Fallback to RSS feeds if no headlines found from SERPAPI
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
                    if published_dt and published_dt < start_of_year_dt:
                        continue
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    published_str = getattr(entry, 'published', '')
                    recent_headlines.append(f"- {published_str}: {title} ({link})")
            recent_headlines = recent_headlines[:5]
        except Exception:
            pass

    # Wikipedia fallback enrichment if still sparse
    if not snapshot_lines or not key_people_lines:
        try:
            wikipedia.set_lang('en')
            search_results = wikipedia.search(company_name, results=1)
            if search_results:
                title = search_results[0]
                try:
                    page = wikipedia.page(title, auto_suggest=False)
                    if not snapshot_lines:
                        try:
                            desc = wikipedia.summary(title, sentences=2, auto_suggest=False)
                            if desc:
                                snapshot_lines.append(f"- Description: {desc}")
                        except Exception:
                            pass
                        if title and not any(line.lower().startswith('- full name:') for line in snapshot_lines):
                            snapshot_lines.append(f"- Full name: {title}")
                    if not key_people_lines:
                        content = getattr(page, 'content', '') or ''
                        m = re.search(r"founder(?:s)?\s*[:\-]\s*(.+?)(?:\n|\.|;)", content, flags=re.IGNORECASE)
                        if m:
                            founders_text = m.group(1).strip()
                            key_people_lines.append(f"- Founders: {founders_text}")
                except Exception:
                    pass
        except Exception:
            pass

    # Construct the information blocks
    headlines_block = "\n".join(recent_headlines) if recent_headlines else "- No external headlines fetched."
    snapshot_block = "\n".join(snapshot_lines) if snapshot_lines else "- No snapshot enrichment."
    key_people_block = "\n".join(key_people_lines) if key_people_lines else "- No key people enrichment."

    # Attempt to get stock data using Yahoo Finance
    ticker_symbol = None
    market_cap_str = "unknown"
    ytd_change_str = "unknown"
    latest_earnings_str = "unknown"
    try:
        def lookup_ticker_via_yahoo(query: str):
            try:
                url = "https://query2.finance.yahoo.com/v1/finance/search"
                params = {"q": query, "quotesCount": 5, "newsCount": 0}
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = requests.get(url, params=params, headers=headers, timeout=6)
                if resp.status_code == 200:
                    print(f"Yahoo Finance search response: {resp.text[:1000]}")  # Debugging output
                    data = resp.json()
                    for q in data.get("quotes", []):
                        symbol = q.get("symbol")
                        quote_type = q.get("quoteType")
                        if symbol and quote_type in ("EQUITY", "ETF", "MUTUALFUND"):
                            return symbol
            except Exception:
                return "yahoo not called"
            return None

        candidates = []
        trimmed = company_name.strip()
        if trimmed:
            common_map = {
                "apple": "AAPL",
                "microsoft": "MSFT",
                "google": "GOOGL",
                "amazon": "AMZN",
                "meta": "META",
                "tesla": "TSLA",
                "nvidia": "NVDA",
            }
            key_lower = trimmed.lower()
            if key_lower in common_map:
                candidates.append(common_map[key_lower])

            found = lookup_ticker_via_yahoo(trimmed)
            if found:
                candidates.append(found)

            up = trimmed.upper()
            if re.fullmatch(r"[A-Z]{1,5}", up):
                candidates.append(up)

        resolved = None
        for symbol in candidates:
            try:
                info = yf.Ticker(symbol).fast_info
                if getattr(info, 'last_price', None) is not None:
                    resolved = symbol
                    break
            except Exception:
                continue

        if resolved:
            ticker_symbol = resolved
            ticker = yf.Ticker(ticker_symbol)
            mc = getattr(ticker.fast_info, 'market_cap', None)
            if mc is not None:
                if mc >= 1_000_000_000_000:
                    market_cap_str = f"~${mc/1_000_000_000_000:.1f}T USD"
                elif mc >= 1_000_000_000:
                    market_cap_str = f"~${mc/1_000_000_000:.1f}B USD"
                elif mc >= 1_000_000:
                    market_cap_str = f"~${mc/1_000_000:.1f}M USD"
                else:
                    market_cap_str = f"~${mc:.0f} USD"

            today = datetime.now().date()
            start_of_year = datetime(today.year, 1, 1).date()
            hist = ticker.history(start=start_of_year, end=today + timedelta(days=1))
            if not hist.empty:
                open_price = hist['Close'].iloc[0]
                last_price = hist['Close'].iloc[-1]
                if open_price and last_price:
                    change_pct = (last_price - open_price) / open_price * 100.0
                    direction = "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat")
                    ytd_change_str = f"{change_pct:.1f}% {direction}"

            try:
                earnings_dates = getattr(ticker, 'earnings_dates', None)
                if callable(earnings_dates):
                    ed = ticker.earnings_dates
                else:
                    ed = getattr(ticker, 'calendar', None)
                cal = getattr(ticker, 'calendar', None)
                if cal is not None and not cal.empty:
                    try:
                        edates = cal.loc['Earnings Date']
                        if hasattr(edates, 'values') and len(edates.values) > 0:
                            latest_earnings_str = str(edates.values[0])
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception as e:
        pass

    finance_block = []
    if ticker_symbol:
        finance_block.append(f"- Stock: {ticker_symbol}; YTD change: {ytd_change_str}")
        finance_block.append(f"- Market Cap: {market_cap_str}")
    else:
        finance_block.append("- Stock: unknown; YTD change: unknown")
        finance_block.append(f"- Market Cap: {market_cap_str}")
    if latest_earnings_str != "unknown":
        finance_block.append(f"- Earnings: {latest_earnings_str}")
    finance_block_str = "\n".join(finance_block)

    # Construct the final response string in the format like the old code
    return f"""
    You are a business research assistant preparing a person for an upcoming meeting with {company_name}.
    As of {end_date}, use only information from the current year to date (from {start_date} to {end_date}).

    1. Company Snapshot:
    {snapshot_block}

    2. Recent Updates (YTD):
    {headlines_block}

    3. Key People:
    {key_people_block}

    4. Business Health (YTD):
    {finance_block_str}
    """
