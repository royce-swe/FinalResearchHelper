import requests
from bs4 import BeautifulSoup
import re
import time
import urllib.parse
from ddgs import DDGS  # ✅ Updated package

# --- CONFIG ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://duckduckgo.com/"
}

MAX_RESULTS = 10
CRAWL_DEPTH = 1
MAX_INTERNAL_LINKS = 5  # ✅ Limit link-following per page
BLOCKED_DOMAINS = ["wikipedia.org", "wikimedia.org", "amazon.com", "imdb.com"]


def search_duckduckgo(query):
    """Perform a DuckDuckGo search using ddgs package."""
    print(f"\n🔎 [DEBUG] Searching DuckDuckGo for: {query}")
    links = []

    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, region="us-en", safesearch="off", max_results=MAX_RESULTS)
            for r in results:
                url = r.get("href") or r.get("url")
                if url and not any(bad in url for bad in BLOCKED_DOMAINS):
                    links.append(url)
    except Exception as e:
        print(f"❌ [DEBUG] Search request failed: {e}")
        return []

    print(f"   → [DEBUG] Found {len(links)} search results")
    for l in links:
        print(f"      • {l}")

    return links


def extract_emails_from_text(text):
    """Extract emails using regex."""
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return re.findall(email_pattern, text)


def scrape_page(url, depth=0, visited=None):
    """Scrape a page for emails, scan text, follow limited internal links."""
    if visited is None:
        visited = set()
    if url in visited or depth > CRAWL_DEPTH:
        return []

    visited.add(url)
    print(f"   → [DEBUG] Crawling page: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"      ⚠️ [DEBUG] Could not load page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    emails = extract_emails_from_text(page_text)

    if emails:
        print(f"      ✅ [DEBUG] Found emails: {emails}")
        return emails

    # ✅ Follow only a few relevant internal links
    if depth < CRAWL_DEPTH:
        domain = urllib.parse.urlparse(url).netloc
        count = 0
        for a in soup.find_all("a", href=True):
            if count >= MAX_INTERNAL_LINKS:
                break
            link = urllib.parse.urljoin(url, a["href"])
            if (
                domain in link
                and link not in visited
                and link.startswith("http")
                and not any(x in link for x in ["#", "Special:", "edit", "login"])
            ):
                print(f"      ↪️ [DEBUG] Following internal link: {link}")
                emails.extend(scrape_page(link, depth + 1, visited))
                count += 1

    return list(set(emails))


def find_email(professor_name, university_name):
    """Try multiple search queries to find professor emails."""
    queries = [
        f'"{professor_name}" "{university_name}" site:.edu email',
        f'"{professor_name}" "{university_name}" faculty site:.edu contact',
        f'"{professor_name}" "{university_name}" professor site:.edu'
    ]

    for query in queries:
        print(f"\n🔎 [DEBUG] Starting search for query: {query}")
        links = search_duckduckgo(query)

        for link in links:
            print(f"   → [DEBUG] Checking: {link}")
            emails = scrape_page(link)
            valid_emails = [
                e for e in emails
                if not e.endswith((".png", ".jpg"))
                and not any(x in e.lower() for x in ["example", "support", "noreply"])
            ]
            if valid_emails:
                print(f"✅ [DEBUG] Found valid email: {valid_emails[0]}")
                return valid_emails[0]
            else:
                print("      ⚠️ [DEBUG] No valid emails found on this page.")
            time.sleep(1)

    print("❌ [DEBUG] No email found after all queries.")
    return "Not Found"


if __name__ == "__main__":
    professor = input("Enter professor name: ").strip()
    university = input("Enter university name: ").strip()

    email = find_email(professor, university)
    print(f"\n✅ Found email: {email}")
