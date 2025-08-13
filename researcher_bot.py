#<<<<<<< HEAD
# import os
# import re
# import io
# import contextlib
# import google.generativeai as genai
# from dotenv import load_dotenv
# from datetime import datetime, timedelta
# import feedparser
# from urllib.parse import quote_plus
# import yfinance as yf
# import requests
# import wikipedia

# # Load the API key from the .env file
# load_dotenv()
# GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# # Configure the Gemini API
# genai.configure(api_key=GOOGLE_API_KEY)

# def get_company_info(company_name: str) -> str:
#     """
#     Sends a structured prompt to the Gemini model to retrieve company information.

#     Args:
#         company_name: The name of the company to research.

#     Returns:
#         A string containing the formatted company research report.
#     """
#     # Compute a Year-To-Date (YTD) window and inject into the prompt to avoid stale info
#     current_date = datetime.now()
#     start_of_year_dt = datetime(current_date.year, 1, 1)
#     start_date = start_of_year_dt.strftime('%Y-%m-%d')
#     end_date = current_date.strftime('%Y-%m-%d')

#     # Prefer SerpAPI enrichment when available; fallback to Google News RSS
#     recent_headlines = []
#     snapshot_lines = []
#     key_people_lines = []
#     if SERPAPI_KEY:
#         # Google News via SerpAPI
#         try:
#             params = {
#                 "engine": "google_news",
#                 "q": company_name,
#                 "when": "365d",
#                 "api_key": SERPAPI_KEY,
#                 "hl": "en",
#                 "gl": "us",
#             }
#             resp = requests.get("https://serpapi.com/search.json", params=params, timeout=8)
#             if resp.status_code == 200:
#                 data = resp.json()
#                 for item in data.get("news_results", [])[:8]:
#                     title = item.get("title")
#                     link = item.get("link")
#                     date = item.get("date") or item.get("published_date") or ""
#                     if title and link:
#                         recent_headlines.append(f"- {date}: {title} ({link})")
#         except Exception:
#             pass

#         # Knowledge Graph snapshot/key people via SerpAPI Google
#         try:
#             params = {
#                 "engine": "google",
#                 "q": f"{company_name} company",
#                 "api_key": SERPAPI_KEY,
#                 "num": "10",
#                 "hl": "en",
#                 "gl": "us",
#             }
#             resp = requests.get("https://serpapi.com/search.json", params=params, timeout=8)
#             if resp.status_code == 200:
#                 data = resp.json()
#                 kg = data.get("knowledge_graph", {}) or {}
#                 if kg:
#                     full_name = kg.get("title")
#                     desc = kg.get("description")
#                     hq = kg.get("headquarters") or kg.get("headquarters_location")
#                     employees = kg.get("employees")
#                     if full_name:
#                         snapshot_lines.append(f"- Full name: {full_name}")
#                     if desc:
#                         snapshot_lines.append(f"- Description: {desc}")
#                     if hq:
#                         snapshot_lines.append(f"- HQ Location: {hq}")
#                     if employees:
#                         snapshot_lines.append(f"- Size: {employees}")
#                     ceo = kg.get("CEO") or kg.get("ceo")
#                     founders = kg.get("Founders") or kg.get("founders")
#                     if ceo:
#                         key_people_lines.append(f"- CEO: {ceo}")
#                     if founders:
#                         key_people_lines.append(f"- Founders: {founders}")
#         except Exception:
#             pass

#     if not recent_headlines:
#         try:
#             def fetch_query_headlines(q: str):
#                 query = quote_plus(q)
#                 rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
#                 return feedparser.parse(rss_url)

#             feeds = []
#             feeds.append(fetch_query_headlines(f'"{company_name}" when:365d'))
#             feeds.append(fetch_query_headlines(f'"{company_name}" site:newsroom.{company_name.lower()}.com when:365d'))
#             feeds.append(fetch_query_headlines(f'"{company_name}" site:investor.{company_name.lower()}.com when:365d'))
#             feeds.append(fetch_query_headlines(f'"{company_name}" (site:reuters.com OR site:bloomberg.com OR site:cnbc.com OR site:wsj.com) when:365d'))

#             start_of_year = start_of_year_dt
#             seen_titles = set()
#             for feed in feeds:
#                 for entry in getattr(feed, 'entries', [])[:10]:
#                     title = getattr(entry, 'title', '')
#                     link = getattr(entry, 'link', '')
#                     published_dt = None
#                     if hasattr(entry, 'published_parsed') and entry.published_parsed:
#                         try:
#                             published_dt = datetime(*entry.published_parsed[:6])
#                         except Exception:
#                             published_dt = None
#                     if published_dt and published_dt < start_of_year:
#                         continue
#                     if not title or title in seen_titles:
#                         continue
#                     seen_titles.add(title)
#                     published_str = ''
#                     if hasattr(entry, 'published'):
#                         published_str = entry.published
#                     recent_headlines.append(f"- {published_str}: {title} ({link})")

#             recent_headlines = recent_headlines[:5]
#         except Exception:
#             pass

#     # Wikipedia fallback enrichment for snapshot/key people if still sparse
#     try:
#         needs_snapshot = len(snapshot_lines) == 0
#         needs_people = len(key_people_lines) == 0
#         if needs_snapshot or needs_people:
#             wikipedia.set_lang('en')
#             search_results = wikipedia.search(company_name, results=1)
#             if search_results:
#                 title = search_results[0]
#                 try:
#                     page = wikipedia.page(title, auto_suggest=False)
#                     # Description from summary
#                     if needs_snapshot:
#                         try:
#                             desc = wikipedia.summary(title, sentences=2, auto_suggest=False)
#                             if desc:
#                                 snapshot_lines.append(f"- Description: {desc}")
#                         except Exception:
#                             pass
#                         # Full name
#                         if title and not any(line.lower().startswith('- full name:') for line in snapshot_lines):
#                             snapshot_lines.append(f"- Full name: {title}")
#                     # Attempt founders from page content
#                     if needs_people:
#                         content = getattr(page, 'content', '') or ''
#                         m = re.search(r"founder(?:s)?\s*[:\-]\s*(.+?)(?:\n|\.|;)", content, flags=re.IGNORECASE)
#                         if m:
#                             founders_text = m.group(1).strip()
#                             key_people_lines.append(f"- Founders: {founders_text}")
#                 except Exception:
#                     pass
#     except Exception:
#         pass

#     headlines_block = "\n".join(recent_headlines) if recent_headlines else "- No external headlines fetched."
#     snapshot_block = "\n".join(snapshot_lines) if snapshot_lines else "- No snapshot enrichment."
#     key_people_enriched_block = "\n".join(key_people_lines) if key_people_lines else "- No key people enrichment."

#     # Attempt to resolve ticker and fetch YTD stock metrics and market cap using Yahoo Finance
#     ticker_symbol = None
#     market_cap_str = "unknown"
#     ytd_change_str = "unknown"
#     latest_earnings_str = "unknown"
#     try:
#         def lookup_ticker_via_yahoo(query: str):
#             try:
#                 url = "https://query2.finance.yahoo.com/v1/finance/search"
#                 params = {"q": query, "quotesCount": 5, "newsCount": 0}
#                 headers = {"User-Agent": "Mozilla/5.0"}
#                 resp = requests.get(url, params=params, headers=headers, timeout=6)
#                 if resp.status_code == 200:
#                     data = resp.json()
#                     for q in data.get("quotes", []):
#                         symbol = q.get("symbol")
#                         quote_type = q.get("quoteType")
#                         if symbol and quote_type in ("EQUITY", "ETF", "MUTUALFUND"):
#                             return symbol
#             except Exception:
#                 return None
#             return None

#         # Build candidates from: common map, Yahoo search, and ticker-like input
#         candidates = []
#         trimmed = company_name.strip()
#         if trimmed:
#             common_map = {
#                 "apple": "AAPL",
#                 "apple inc": "AAPL",
#                 "microsoft": "MSFT",
#                 "google": "GOOGL",
#                 "alphabet": "GOOGL",
#                 "amazon": "AMZN",
#                 "meta": "META",
#                 "tesla": "TSLA",
#                 "nvidia": "NVDA",
#             }
#             key_lower = trimmed.lower()
#             if key_lower in common_map:
#                 candidates.append(common_map[key_lower])

#             found = lookup_ticker_via_yahoo(trimmed)
#             if found:
#                 candidates.append(found)

#             up = trimmed.upper()
#             if re.fullmatch(r"[A-Z]{1,5}", up):
#                 candidates.append(up)

#         resolved = None
#         for symbol in candidates:
#             try:
#                 with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
#                     info = yf.Ticker(symbol).fast_info
#                     if getattr(info, 'last_price', None) is not None:
#                         resolved = symbol
#                         break
#             except Exception:
#                 continue

#         if resolved:
#             ticker_symbol = resolved
#             ticker = yf.Ticker(ticker_symbol)
#             # Market cap
#             mc = getattr(ticker.fast_info, 'market_cap', None)
#             if mc is not None:
#                 if mc >= 1_000_000_000_000:
#                     market_cap_str = f"~${mc/1_000_000_000_000:.1f}T USD"
#                 elif mc >= 1_000_000_000:
#                     market_cap_str = f"~${mc/1_000_000_000:.1f}B USD"
#                 elif mc >= 1_000_000:
#                     market_cap_str = f"~${mc/1_000_000:.1f}M USD"
#                 else:
#                     market_cap_str = f"~${mc:.0f} USD"

#             # YTD change
#             today = datetime.now().date()
#             start_of_year = datetime(today.year, 1, 1).date()
#             hist = ticker.history(start=start_of_year, end=today + timedelta(days=1))
#             if not hist.empty:
#                 open_price = hist['Close'].iloc[0]
#                 last_price = hist['Close'].iloc[-1]
#                 if open_price and last_price:
#                     change_pct = (last_price - open_price) / open_price * 100.0
#                     direction = "up" if change_pct > 0 else ("down" if change_pct < 0 else "flat")
#                     ytd_change_str = f"{change_pct:.1f}% {direction}"

#             # Recent earnings (last available)
#             try:
#                 earnings_dates = getattr(ticker, 'earnings_dates', None)
#                 if callable(earnings_dates):
#                     ed = ticker.earnings_dates
#                 else:
#                     ed = getattr(ticker, 'calendar', None)
#                 # Fallback: use calendar info
#                 cal = getattr(ticker, 'calendar', None)
#                 if cal is not None and not cal.empty:
#                     # calendar index may include 'Earnings Date'
#                     try:
#                         edates = cal.loc['Earnings Date']
#                         if hasattr(edates, 'values') and len(edates.values) > 0:
#                             latest_earnings_str = str(edates.values[0])
#                     except Exception:
#                         pass
#             except Exception:
#                 pass
#     except Exception:
#         pass

#     finance_block = []
#     if ticker_symbol:
#         finance_block.append(f"- Stock: {ticker_symbol}; YTD change: {ytd_change_str}")
#         finance_block.append(f"- Market Cap: {market_cap_str}")
#     else:
#         finance_block.append("- Stock: unknown; YTD change: unknown")
#         finance_block.append(f"- Market Cap: {market_cap_str}")
#     if latest_earnings_str != "unknown":
#         finance_block.append(f"- Earnings: {latest_earnings_str}")
#     finance_block_str = "\n".join(finance_block)

#     # Create the prompt for the Gemini model
#     prompt = f"""
#     You are a business research assistant preparing a person for an upcoming meeting with {company_name}.
#     As of {end_date}, use only information from the current year to date (from {start_date} to {end_date}). If no reliable updates are found in this window, say: "No YTD updates."
#     Retrieve the latest and most relevant information from credible sources.
#     Present it in a concise, scannable format that can be read in under 45 seconds.
#     Use short bullet points under the following sections:

#    1. Company Snapshot
 
# Full name, logo (if possible), industry, HQ location, size (employee range), and 1–sentence description

#     2. Recent Updates (YTD)

#     2–3 short headlines with date and impact (e.g., funding, product launch, leadership changes, acquisitions, partnerships).

#     3. Key People (must always be populated)

#     Enriched from public sources (if available):
#     {key_people_enriched_block}

#     - Provide at least CEO and one other top executive (e.g., CFO/COO/CTO or equivalent). Prefer official titles.
#     - If available within YTD, include leadership changes with date (e.g., "Jun 2025: New CFO appointed").
#     - If uncertain, provide best-known executives and add "confidence: low".
#     - Do not ask the user for names or say they must be provided; infer from public knowledge.

#     4. Business Health (YTD, concise)

#     Factual metrics:
#     {finance_block_str}

#     Then add:
#     - Guidance/Outlook: 1 short line if available; otherwise say "no formal guidance YTD".
#     - Funding (if private): Last round, date, amount, lead investor; else "N/A (public)".
#     - Notes: Any major risk/controversy YTD in one short line.
#     - Sources: List 1–2 links from the headlines above (do not fabricate URLs).

#     5. External Headlines (context, YTD)

#     {headlines_block}

#     Enriched Snapshot (if any):
#     {snapshot_block}

#     Hard requirements:
#     - Never request the company name (it is already provided as {company_name}).
#     - Keep responses short and scannable; avoid paragraphs longer than two lines.
#     - If information is not available YTD, state so briefly and move on.

#     Prioritize accuracy, recency, and brevity. Avoid unnecessary detail or long paragraphs."""

#     # Use the 'gemini-1.5-flash' model
#     model = genai.GenerativeModel('gemini-1.5-flash')
    
#     # Generate the content based on the prompt
#     try:
#         response = model.generate_content(prompt)
#         return response.text
#     except Exception as e:
#         return f"An error occurred: {e}"

# if __name__ == "__main__":
#     print("Welcome to the Gemini Company Researcher!")
#     while True:
#         company = input("Enter a company name (or 'exit' to quit): ")
#         if company.lower() == 'exit':
#             break
        
#         print("\nGathering information...\n")
#         report = get_company_info(company)
#         print(report)
#         print("-" * 50)





#=======
#>>>>>>> 9b445b8321e288105f8ab099fb2ebb489a697ec9
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
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Load the API key from the .env file
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Configure the Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

app = FastAPI()

# Define the request body model
class CompanyRequest(BaseModel):
    company_name: str


def get_company_info(company_name: str) -> str:
    """
    Sends a structured prompt to the Gemini model to retrieve company information.
    """
    current_date = datetime.now()
    start_of_year_dt = datetime(current_date.year, 1, 1)
    start_date = start_of_year_dt.strftime('%Y-%m-%d')
    end_date = current_date.strftime('%Y-%m-%d')

    recent_headlines = []
    snapshot_lines = []
    key_people_lines = []
    
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
                    full_name = kg.get("title")
                    desc = kg.get("description")
                    hq = kg.get("headquarters") or kg.get("headquarters_location")
                    employees = kg.get("employees")
                    if full_name:
                        snapshot_lines.append(f"- Full name: {full_name}")
                    if desc:
                        snapshot_lines.append(f"- Description: {desc}")
                    if hq:
                        snapshot_lines.append(f"- HQ Location: {hq}")
                    if employees:
                        snapshot_lines.append(f"- Size: {employees}")
                    ceo = kg.get("CEO") or kg.get("ceo")
                    founders = kg.get("Founders") or kg.get("founders")
                    if ceo:
                        key_people_lines.append(f"- CEO: {ceo}")
                    if founders:
                        key_people_lines.append(f"- Founders: {founders}")
        except Exception:
            pass

    if not recent_headlines:
        try:
            def fetch_query_headlines(q: str):
                query = quote_plus(q)
                rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
                return feedparser.parse(rss_url)

            feeds = []
            feeds.append(fetch_query_headlines(f'"{company_name}" when:365d'))
            feeds.append(fetch_query_headlines(f'"{company_name}" site:newsroom.{company_name.lower()}.com when:365d'))
            feeds.append(fetch_query_headlines(f'"{company_name}" site:investor.{company_name.lower()}.com when:365d'))
            feeds.append(fetch_query_headlines(f'"{company_name}" (site:reuters.com OR site:bloomberg.com OR site:cnbc.com OR site:wsj.com) when:365d'))

            start_of_year = start_of_year_dt
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
                            published_dt = None
                    if published_dt and published_dt < start_of_year:
                        continue
                    if not title or title in seen_titles:
                        continue
                    seen_titles.add(title)
                    published_str = ''
                    if hasattr(entry, 'published'):
                        published_str = entry.published
                    recent_headlines.append(f"- {published_str}: {title} ({link})")

            recent_headlines = recent_headlines[:5]
        except Exception:
            pass

    headlines_block = "\n".join(recent_headlines) if recent_headlines else "- No external headlines fetched."
    snapshot_block = "\n".join(snapshot_lines) if snapshot_lines else "- No snapshot enrichment."
    key_people_enriched_block = "\n".join(key_people_lines) if key_people_lines else "- No key people enrichment."

    finance_block = []
    finance_block_str = "\n".join(finance_block)

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
    {key_people_enriched_block}

    4. Business Health (YTD, concise)
    {finance_block_str}
    """

    # Use the 'gemini-1.5-flash' model
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"


@app.post("/company-info/")
async def company_info(request: CompanyRequest):
    company_name = request.company_name
    try:
        report = get_company_info(company_name)
        return {"company_name": company_name, "report": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
