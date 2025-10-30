# =========================================================
# Imports
# =========================================================

from pathlib import Path
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import pandas as pd
import time
from functools  import lru_cache, wraps
from rapidfuzz import fuzz
from pyalex import Works, Authors, Sources, Institutions, Topics, Publishers, Funders, config
import pyalex
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
from ddgs import DDGS
from openai import OpenAI
import os
import unicodedata
import bcrypt
import json
from threading import RLock
import uuid, hashlib  # NEW for metrics
import mysql.connector
from mysql.connector import Error
import random
import jwt
import datetime


# =========================================================
# Flask App Configuration
# =========================================================

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config["SECRET_KEY"] = "wetsocks4life"

CORS(
    app,
    origins=["http://localhost:5173", "https://researchconnectai.com", "https://www.researchconnectai.com"],
    supports_credentials=True
)

# AI -----------------------
# USE THE API key on ur local environment to run the email generator
# run this in the terminal
# export OPENAI_API_KEY="put code here"


client = OpenAI()
pyalex.config.email = "jalenmathis7@gmail.com"

# -------- Faculty directory base --------
FACULTY_DIR = (Path(__file__).resolve().parent / "Faculty")

# =========================================================
# In-Memory & Persistent Data Structures
# =========================================================

# In-memory cache for found emails: (name_lower, uni_lower) -> email
EMAIL_CACHE = {}
EMAIL_CACHE_FILE = (Path(__file__).resolve().parent / "email_cache.json")
EMAIL_CACHE_LOCK = RLock()

DISPLAY_NAME_MAP = {
    "Caltech": "California Institute of Technology",
    "CMU": "Carnegie Mellon University",
    "Columbia": "Columbia University",
    "FAU": "Florida Atlantic University",
    "FSU": "Florida State University",
    "MIT": "Massachusetts Institute of Technology",
    "Princeton": "Princeton University",
    "Purdue": "Purdue University",
    "Stanford": "Stanford University",
    "UCF": "University of Central Florida",
    "UF": "University of Florida",
    "UM": "University of Miami",          # confirm this is Miami (not Michigan)
    "UPENN": "University of Pennsylvania",
    "UW": "University of Washington",     # confirm this is Washington (not Wisconsin)
    "UWMadison": "University of Wisconsin–Madison",
    "GeorgiaTech": "Georgia Institute of Technology",
}

OBFUSCATION_PATTERNS = [
    (r"\s*\[?\(?\s*at\s*\)?\]?\s*", "@"),   # [at], (at),  at 
    (r"\s*\[?\(?\s*dot\s*\)?\]?\s*", "."),  # [dot], (dot),  dot 
]

# -------------------- Email cache persistence --------------------
def _load_email_cache():
    if EMAIL_CACHE_FILE.exists():
        try:
            with open(EMAIL_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    EMAIL_CACHE.update(data)
        except Exception as e:
            print(f"[WARN] Failed to load email cache: {e}")

def _save_email_cache():
    try:
        with EMAIL_CACHE_LOCK:
            tmp = EMAIL_CACHE_FILE.with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(EMAIL_CACHE, f, ensure_ascii=False, indent=2)
            tmp.replace(EMAIL_CACHE_FILE)
    except Exception as e:
        print(f"[WARN] Failed to save email cache: {e}")

def remember_email(name: str, university: str, email: str):
    if not email or email in ("Not Available",):
        return
    key = (name.lower().strip(), _normalize_uni(university).lower().strip())
    with EMAIL_CACHE_LOCK:
        if EMAIL_CACHE.get(str(key)) == email:
            return
        EMAIL_CACHE[str(key)] = email
    _save_email_cache()

_load_email_cache()

def write_back_email_to_csv(uni: str, dept_slug: str, name: str, email: str):
    # Only persist clearly trustworthy emails
    if not email or not email.lower().endswith(".edu"):
        return
    path = FACULTY_DIR / uni / f"{dept_slug}.csv"
    if not path.exists():
        return
    try:
        df = pd.read_csv(path)
        cols = [c.strip().lower() for c in df.columns]
        df.columns = cols

        name_col = next((c for c in cols if c in ("name","full name","professor","professor_name")), None)
        email_col = next((c for c in cols if "email" in c), None)
        if not name_col:
            return
        if not email_col:
            email_col = "email"
            df[email_col] = ""

        target_slug = _slugify_name(name)
        idx = None
        for i, r in df.iterrows():
            if _slugify_name(str(r.get(name_col, ""))) == target_slug:
                idx = i
                break
        if idx is None:
            return

        current = str(df.at[idx, email_col] or "").strip()
        # Replace only if blank/invalid
        if not is_valid_email_text(current):
            df.at[idx, email_col] = email
            tmp = path.with_suffix(".tmp.csv")
            df.to_csv(tmp, index=False, encoding="utf-8")
            tmp.replace(path)
    except Exception as e:
        print(f"[WARN] write_back_email_to_csv failed for {uni}/{dept_slug}: {e}")

def _slugify_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-")
    return s.lower()

# Common acronyms/aliases -> canonical names to improve hit rate
UNI_ALIASES = {
    "uiuc": "University of Illinois Urbana-Champaign",
    "georgia tech": "Georgia Institute of Technology",
    "MIT": "Massachusetts Institute of Technology",
    "uc berkeley": "University of California, Berkeley",
    "uc san diego": "University of California, San Diego",
    "ucsd": "University of California, San Diego",
    "UWMadison": "University of Wisconsin–Madison",
    "ucla": "University of California, Los Angeles",
    "uc los angeles": "University of California, Los Angeles",
    "CMU": "Carnegie Mellon University",
    "ut austin": "The University of Texas at Austin",
    "caltech": "California Institute of Technology",
    "university of florida": "University of Florida",
    "uf": "University of Florida",
    "purdue": "Purdue University",
    "stanford": "Stanford University",
}

# =========================================================
# Utility Functions
# =========================================================

def _normalize_uni(u: str) -> str:
    if not u:
        return u
    # Case-insensitive lookup into DISPLAY_NAME_MAP
    for k, v in DISPLAY_NAME_MAP.items():
        if k.lower() == u.strip().lower():
            return v
    key = u.strip().lower()
    return UNI_ALIASES.get(key, u)

def _best_inst_match_score(author_insts, target_uni) -> int:
    if not author_insts:
        return 0
    target = (target_uni or "").lower().strip()
    best = 0
    for inst in author_insts:
        name = (inst.get("display_name") or "").lower()
        if not name:
            continue
        score = max(
            fuzz.partial_ratio(name, target),
            fuzz.partial_ratio(target, name),
        )
        if score > best:
            best = score
    return best


# =========================================================
# Configuration
# =========================================================
OPENALEX_MAILTO = "jalenmathis7@gmail.com"  # polite pool
OPENALEX_BASE = "https://api.openalex.org"

HEADERS = {
    "User-Agent": f"ResearchHelper/1.0 (mailto:{OPENALEX_MAILTO})"
}

# =========================================================
# Helper Function
# =========================================================
def _normalize_name(name: str) -> str:
    # Optional: normalize whitespace, remove accents, etc.
    return " ".join(name.split())

def _normalize_uni(uni: str) -> str:
    # Optional: normalize university names, lowercase, remove punctuation
    return uni.lower().strip()

def _fuzzy_match_institution(hint: str, uni_norm: str, threshold: int = 70) -> bool:
    if not hint:
        return False
    score = fuzz.ratio(hint.lower(), uni_norm)
    return score >= threshold

# =========================================================
# Main Function
# =========================================================
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0  # seconds
BACKOFF_MULTIPLIER = 1.5

@lru_cache(maxsize=1000)
def get_openalex_id_for_prof(name: str, university: str, *, fuzzy_threshold: int = 70) -> str:
    """
    Search for a professor in OpenAlex using autocomplete API with rate-limit handling.
    Returns OpenAlex author ID (short_id) or fallback if not found.
    """
    base_url = "https://api.openalex.org/autocomplete/authors"
    query = requests.utils.quote(name)
    url = f"{base_url}?q={query}"

    retry_delay = INITIAL_BACKOFF

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 429:
                # Rate limit hit
                print(f"[WARN] 429 hit for {name}, retrying in {retry_delay:.1f}s")
                time.sleep(retry_delay)
                retry_delay *= BACKOFF_MULTIPLIER
                continue
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])

            # Find best match by fuzzy name + university
            best_id, best_score = "", -1
            for author in results:
                author_name = author.get("display_name", "")
                hint = author.get("hint", "")
                works_count = author.get("works_count", 0)

                # Use fuzzy match on university if hint exists
                score = 0
                if hint:
                    score = fuzz.token_set_ratio(university.lower(), hint.lower())

                # Prioritize higher score + works count
                if score > best_score or (score == best_score and works_count > 0):
                    best_score = score
                    best_id = author.get("short_id", "")

            if best_id:
                return best_id

            print(f"[WARN] No good OpenAlex match for {name}")
            return ""  # not found

        except requests.exceptions.RequestException as e:
            print(f"[WARN] Attempt {attempt+1} failed for {name}: {e}")
            time.sleep(retry_delay)
            retry_delay *= BACKOFF_MULTIPLIER

    print(f"[WARN] Could not retrieve authors for {name} after {MAX_RETRIES} retries")
    return best_id  # fallback


# @lru_cache(maxsize=1000)
# def get_openalex_id_for_prof(name: str, university: str, *, fuzzy_threshold: int = 70) -> str:
#     # Tuned fuzzy down to 70 from 80
#     """
#     Robust ID finder:
#       1) Normalize university name (map acronyms/aliases).
#       2) Try filtering Authors by institution ID AND name.
#       3) Fallback: search by name only and fuzzy-match institutions.
#     Returns '' if not found quickly.
#     """
#     best_id =''
#     try:
#         t0 = time.time()
#         uni_norm = _normalize_uni(university)

#         # --- Try to resolve institution ID first
#         try:
#             insts = list(
#                 Institutions()
#                 .search(uni_norm)
#                 .select(["id", "display_name"])
#                 .get()
#             )
#         except Exception:
#             insts = []

#         if insts:
#             inst_id = insts[0].get("id")
#             if inst_id:
#                 try:
#                     candidates_iter = (
#                         Authors()
#                         .filter(**{
#                             "last_known_institutions.id": inst_id,
#                             "display_name.search": name,
#                         })
#                         .select(["id", "display_name", "last_known_institutions", "works_count"])
#                         .paginate(per_page=25)
#                     )
#                     best_id, best_score, best_works = "", -1, -1
#                     for page in candidates_iter:
#                         for a in page:
#                             score = _best_inst_match_score(a.get("last_known_institutions", []), uni_norm)
#                             works = int(a.get("works_count") or 0)
#                             if score > best_score or (score == best_score and works > best_works):
#                                 best_score, best_works = score, works
#                                 best_id = (a.get("id") or "").split("/")[-1]
#                         if time.time() - t0 > 10.0:  # soft guard changed from 3 to 10
#                             break
#                     if best_id and best_score >= fuzzy_threshold:
#                         return best_id
#                 except Exception as e:
#                     print(f"[WARN] OpenAlex filter-by-inst failed for {name} @ {uni_norm}: {e}")

#         # --- Fallback: search by name; fuzzy on institution names
#         try:
#             candidates_iter = (
#                 Authors()
#                 .search(name)
#                 .select(["id", "display_name", "last_known_institutions", "works_count"])
#                 .paginate(per_page=40)
#             )
#             best_id, best_score, best_works = "", -1, -1
#             for page in candidates_iter:
#                 for a in page:
#                     score = _best_inst_match_score(a.get("last_known_institutions", []), uni_norm)
#                     works = int(a.get("works_count") or 0)
#                     if score > best_score or (score == best_score and works > best_works):
#                         best_score, best_works = score, works
#                         best_id = (a.get("id") or "").split("/")[-1]
#                 if time.time() - t0 > 15.0: #changed from 5 to 5
#                     break
#             if best_id and best_score >= fuzzy_threshold:
#                 return best_id
#         except Exception as e:
#             print(f"[WARN] OpenAlex name-search failed for {name} @ {uni_norm}: {e}")

#     except Exception as e:
#         print(f"[WARN] get_openalex_id_for_prof unexpected error: {e}")

#     print(f"Found open alex id for {name}: {best_id}")
#     if (best_id == ''):
#         best_id = "A5007769527" #Fall back for testing

#     return best_id

def prettify_department(filename: str, uni_prefix: str) -> str:
    """
    Turn 'caltech_computer_science.csv' -> 'Computer Science'.
    If filename starts with '<uni>_', strip that prefix first.
    """
    base = Path(filename).stem
    pref = f"{uni_prefix.lower()}_"
    if base.lower().startswith(pref):
        base = base[len(pref):]
    return base.replace("_", " ").strip().title()

def list_universities_and_departments():
    """
    Scan backend/Faculty/ to build the dropdown data.
    Returns:
    {
      "universities":[
        {"name":"Caltech","slug":"Caltech","departments":[{"name":"Computer Science","slug":"caltech_computer_science"}, ...]},
        ...
      ]
    }
    """
    universities = []
    if not FACULTY_DIR.exists():
        return {"universities": universities}

    for uni_dir in sorted([p for p in FACULTY_DIR.iterdir() if p.is_dir()]):
        uni_name = uni_dir.name  # e.g., "Caltech"
        departments = []
        for f in sorted(uni_dir.glob("*.csv")):
            dept_slug = f.stem
            dept_name = prettify_department(f.name, uni_name)
            departments.append({"name": dept_name, "slug": dept_slug})
        if departments:
            universities.append({"name": uni_name, "slug": uni_name, "departments": departments})
    return {"universities": universities}

def is_valid_email_text(text: str, prefer_domain: str | None = None) -> str | None:
    """
    Validate and normalize a text that might contain an email.
    - Reject placeholders like 'email protected'
    - Deobfuscate common patterns
    - Extract the first reasonable email (favor .edu and/or prefer_domain)
    """
    if not text:
        return None

    raw = text.strip()
    lower = raw.lower()
    if "protected" in lower and "email" in lower:
        return None

    # Deobfuscate common 'at'/'dot' patterns
    cleaned = raw
    for pat, repl in OBFUSCATION_PATTERNS:
        cleaned = re.sub(pat, repl, cleaned, flags=re.IGNORECASE)

    # Extract emails
    found = re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", cleaned)
    if not found:
        return None

    # Prefer .edu
    edu_emails = [e for e in found if e.lower().endswith(".edu")]
    if edu_emails:
        if prefer_domain:
            prefer_domain = prefer_domain.lower()
            prioritized = [e for e in edu_emails if e.lower().endswith(prefer_domain)]
            if prioritized:
                return prioritized[0]
        return edu_emails[0]

    return found[0] if found else None

def extract_emails_from_soup(soup: BeautifulSoup) -> list[str]:
    """Look for mailto links in addition to page text."""
    emails = set()

    # mailto: links
    for a in soup.select('a[href^="mailto:"]'):
        href = a.get("href", "")
        candidate = href.replace("mailto:", "").strip()
        if candidate:
            norm = is_valid_email_text(candidate)
            if norm:
                emails.add(norm)

    # page text
    page_text = soup.get_text(" ", strip=True)
    for e in extract_emails_from_text(page_text):
        norm = is_valid_email_text(e)
        if norm:
            emails.add(norm)

    return list(emails)

@app.route('/draft-email', methods=['POST'])
def draft_email():
    try:
        data = request.get_json()

        student_name = data.get("student_name", "Your Name")
        student_interests = data.get("student_research_interests", "")
        student_skills = data.get("student_skills", "")
        professor = data.get("professor", {})

        professor_name = professor.get("name", "Professor")
        research_areas = ", ".join(professor.get("researchAreas", [])) or "your field of research"
        papers = professor.get("recentPapers", [])

        notable_paper = ""
        if papers:
            notable_paper = f"your paper titled '{papers[0]['title']}' which explores {papers[0].get('abstract', 'an interesting area in your research')}."

        # Prepare prompt
        email_prompt = f"""
        Subject: Inquiry About Research Opportunities
        Dear Professor [Last Name],
        I hope this email finds you well. My name is {student_name}, and I am a high school student passionate about {student_interests}. 
        I am reaching out to express my strong interest in your research on {research_areas}.
        I was particularly intrigued by {notable_paper}
        Given my background in {student_skills}, I believe I could contribute meaningfully to your research.
        Please let me know if you have any volunteer openings or if you could refer me to somebody who might have an opportunity for me. 
        I appreciate your time and consideration and look forward to hearing from you.
        Best regards,
        {student_name}
        [Email: placeholder@domain.com]
        """

        # ✅ New OpenAI client usage
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that writes professional outreach emails for students contacting professors about research opportunities."},
                {"role": "user", "content": email_prompt}
            ],
            max_tokens=350,
            temperature=0.7
        )

        email_draft = response.choices[0].message.content.strip()

        return jsonify({"draft": email_draft}), 200

    except Exception as e:
        print("Error generating draft:", e)
        return jsonify({"error": "Failed to generate email draft"}), 500

# -------- CONFIGURATION --------
config.email = "jalenmathis7@gmail.com"
FUZZY_MATCH_THRESHOLD = 90  # Increased sensitivity
MIN_MATCH_COUNT = 2         # Require at least this many strong matches

# ---------- EMAIL SCRAPER UTILS (Updated) ----------
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://duckduckgo.com/"
}

SEARCH_URL = "https://duckduckgo.com/html/"
MAX_RESULTS = 10
CRAWL_DEPTH = 1
MAX_INTERNAL_LINKS = 5
BLOCKED_DOMAINS = ["wikipedia.org", "wikimedia.org", "amazon.com", "imdb.com"]

def search_duckduckgo(query):
    """Perform a DuckDuckGo search using ddgs package, only return .edu URLs."""
    print(f"\n🔎 [DEBUG] Searching DuckDuckGo for: {query}")
    links = []

    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, region="us-en", safesearch="off", max_results=MAX_RESULTS)
            for r in results:
                url = r.get("href") or r.get("url")
                if url:
                    parsed = urllib.parse.urlparse(url)
                    domain = parsed.netloc.lower()
                    if domain.endswith(".edu") and not any(bad in domain for bad in BLOCKED_DOMAINS):
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

def scrape_page(url, depth=0, visited=None, prefer_domain: str | None = None):
    """Scrape a page for emails, scan text + mailto:, follow limited internal links."""
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
    emails = extract_emails_from_soup(soup)

    if emails:
        print(f"      ✅ [DEBUG] Found emails (raw): {emails}")
        validated = []
        for e in emails:
            v = is_valid_email_text(e, prefer_domain=prefer_domain)
            if v:
                validated.append(v)
        if validated:
            return list(dict.fromkeys(validated))  # de-dup preserving order

    # Follow only a few relevant internal links
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
                found = scrape_page(link, depth + 1, visited, prefer_domain=prefer_domain)
                if found:
                    return found
                count += 1

    return []

# ---------------- NEW ENDPOINT: fetch recent papers ----------------
def fetch_recent_papers(author_id, max_papers=5):
    """
    Fetch up to max_papers recent works for an OpenAlex author.
    Handles 429 rate-limits with exponential backoff.
    Accepts either short IDs (A123...) or full URLs.
    """
    papers = []

    # Normalize to short ID if full URL is passed
    if author_id.startswith("https://openalex.org/authors/"):
        short_id = author_id.split("/")[-1]
    else:
        short_id = author_id

    base_url = "https://api.openalex.org/works"
    url = (
        f"{base_url}?filter=authorships.author.id:{short_id}"
        f"&sort=publication_year:desc"
        f"&select=title,publication_year,primary_location,cited_by_count,abstract_inverted_index"
        f"&per-page=20"
    )

    retry_delay = INITIAL_BACKOFF

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 429:
                print(f"[WARN] 429 hit for {short_id}, retrying in {retry_delay:.1f}s")
                time.sleep(retry_delay)
                retry_delay *= BACKOFF_MULTIPLIER
                continue
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])

            for work in results[:max_papers]:
                title = work.get("title") or "Untitled"
                year = work.get("publication_year") or "N/A"
                journal = ((work.get("primary_location") or {}).get("source") or {}).get("display_name") or "Unknown Journal"
                citations = work.get("cited_by_count") or 0

                # Rebuild abstract from inverted index if present
                abstract_data = work.get("abstract_inverted_index") or {}
                if isinstance(abstract_data, dict) and abstract_data:
                    words_sorted = sorted(abstract_data.items(), key=lambda kv: kv[1][0] if kv[1] else 0)
                    abstract = " ".join(word for word, _ in words_sorted)
                else:
                    abstract = "No abstract available."

                papers.append({
                    "title": title,
                    "year": year,
                    "journal": journal,
                    "citations": citations,
                    "abstract": abstract,
                })

            return papers

        except requests.exceptions.RequestException as e:
            print(f"[WARN] Attempt {attempt+1} failed for {short_id}: {e}")
            time.sleep(retry_delay)
            retry_delay *= BACKOFF_MULTIPLIER

    print(f"[WARN] Could not fetch papers for {short_id} after {MAX_RETRIES} retries")
    return papers


# ---------------- NEW ENDPOINT: get professor details by ID ----------------
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0
BACKOFF_MULTIPLIER = 1.5

def get_author_with_retry(oa_id, max_retries=MAX_RETRIES, backoff=INITIAL_BACKOFF):
    """
    Fetch an OpenAlex author with retry/backoff for 429s.
    Accepts short ID or full URL.
    """
    if not str(oa_id).startswith("http"):
        oa_id = f"https://openalex.org/{oa_id}"

    delay = backoff
    for attempt in range(max_retries):
        try:
            author = Authors()[oa_id]
            return author
        except Exception as e:
            if "429" in str(e) or "too many 429" in str(e):
                print(f"[WARN] 429 hit for {oa_id}, retrying in {delay:.1f}s")
                time.sleep(delay + random.random() * 0.5)
                delay *= BACKOFF_MULTIPLIER
                continue
            else:
                print(f"[WARN] Failed to fetch {oa_id}: {e}")
                break
    print(f"[WARN] Could not fetch author {oa_id} after {max_retries} retries")
    return None


@app.route("/professors/<prof_id>", methods=["GET"])
def get_professor_details(prof_id):
    try:
        # Normalize OpenAlex IDs to the short form
        if prof_id.startswith("http") or prof_id.startswith("openalex.org"):
            prof_id = prof_id.split("/")[-1]

        # Handle CSV-based IDs: csv::<uni>::<dept>::<slug-name>
        if prof_id.startswith("csv::"):
            _, uni, dept_slug, slug_name = prof_id.split("::", 3)
            csv_path = FACULTY_DIR / uni / f"{dept_slug}.csv"
            if not csv_path.exists():
                return jsonify({"error": "Professor not found"}), 404

            df = pd.read_csv(csv_path)
            df.columns = [c.strip().lower() for c in df.columns]
            name_col = next((c for c in df.columns if c in ("name", "full name", "professor", "professor_name")), None)
            title_col = next((c for c in df.columns if c in ("title", "position", "role")), None)
            email_col = next((c for c in df.columns if "email" in c), None)
            research_col = next((c for c in df.columns if "research" in c or "area" in c or "interests" in c), None)

            if not name_col:
                return jsonify({"error": "Professor not found"}), 404

            match_row = None
            for _, r in df.iterrows():
                candidate = str(r.get(name_col, "")).strip()
                if _slugify_name(candidate) == slug_name:
                    match_row = r
                    break
            if match_row is None:
                return jsonify({"error": "Professor not found"}), 404

            name = str(match_row.get(name_col, "")).strip()
            title = str(match_row.get(title_col, "")).strip() if title_col else ""
            raw_email = str(match_row.get(email_col, "")).strip() if email_col else ""
            csv_research = str(match_row.get(research_col, "")).strip() if research_col else ""

            email = is_valid_email_text(raw_email) or "Not Available"

            # Enrich from OpenAlex with retry/backoff
            oa_id = get_openalex_id_for_prof(name, uni)
            research_areas, recent_papers = [], []

            if oa_id:
                author = get_author_with_retry(oa_id)
                if author:
                    xconcepts = author.get("x_concepts") or []
                    research_areas = [c.get("display_name") for c in xconcepts if c.get("display_name")]
                    recent_papers = fetch_recent_papers(oa_id)  # already has retry/backoff
            # fallback to CSV research text
            if not research_areas and csv_research:
                research_areas = [s.strip() for s in re.split(r"[;,]", csv_research) if s.strip()]

            professor_info = {
                "id": prof_id,
                "name": name,
                "email": email,
                "university": uni,
                "department": dept_slug,
                "title": title,
                "researchAreas": research_areas,
                "biography": f"{name} is a faculty member at {uni}.",
                "recentPapers": recent_papers
            }
            return jsonify(professor_info), 200

        # ---------- Pure OpenAlex ID path ----------
        full_oa_id = f"https://openalex.org/{prof_id}"
        author = get_author_with_retry(full_oa_id)
        if not author:
            return jsonify({"error": "Professor not found"}), 404

        name = author.get("display_name", "Unknown")
        institutions = author.get("last_known_institutions", [])
        university = institutions[0]["display_name"] if institutions else "Unknown Institution"
        works_count = author.get("works_count", 0)
        topics = [c.get("display_name") for c in (author.get("x_concepts") or []) if c.get("display_name")]

        recent_papers = fetch_recent_papers(full_oa_id)  # safe retry logic included

        professor_info = {
            "id": prof_id,
            "name": name,
            "email": "Not Available",
            "university": university,
            "department": "Professor",
            "researchAreas": topics,
            "biography": f"{name} is a professor at {university} with {works_count} publications.",
            "recentPapers": recent_papers
        }
        return jsonify(professor_info), 200

    except Exception as e:
        print(f"Error fetching professor details: {e}")
        return jsonify({"error": "Failed to fetch professor details"}), 500


# --- NEW IMPROVED MATCH FUNCTION ---
GENERIC_WORDS = {
    "science", "research", "study", "education", "academic",
    "philosophy", "social science", "general", "medicine",
    "law", "political science", "public policy", "history",
    "economics", "management", "business", "library science"
}

def clean_topics(topics):
    """Remove overly generic research topics before matching."""
    return [
        t for t in topics
        if t and t.lower().strip() not in GENERIC_WORDS
    ]

def matches_interests(topics, interests, threshold=FUZZY_MATCH_THRESHOLD, min_matches=MIN_MATCH_COUNT):
    """
    Return True if at least `min_matches` of user interests fuzzy-match
    the professor's topics with a score >= threshold.
    """
    count = 0
    interests_norm = [i.lower().strip() for i in interests]
    topics_norm = [t.lower().strip() for t in clean_topics(topics)]

    for interest in interests_norm:
        for topic in topics_norm:
            score = fuzz.partial_ratio(interest, topic)
            if score >= threshold:
                count += 1
                if count >= min_matches:
                    return True
    return False

def get_top_research_matches(topics, interests, threshold=FUZZY_MATCH_THRESHOLD, top_n=2):
    """
    Return up to top_n topics that strongly match interests,
    plus a 3rd fallback topic (first topic if not already included).
    """
    interests_norm = [i.lower().strip() for i in interests]
    topics_norm = [t.lower().strip() for t in clean_topics(topics)]

    # Score topics against interest
    scored_topics = []
    for topic in topics_norm:
        max_score = max(fuzz.partial_ratio(topic, interest) for interest in interests_norm)
        if max_score >= threshold:
            scored_topics.append((topic, max_score))

    # Sort by score
    scored_topics.sort(key=lambda x: x[1], reverse=True)
    top_matches = [t for t, score in scored_topics[:top_n]]

    # Add fallback topic
    if topics_norm:
        first_topic = topics_norm[0]
        if first_topic not in top_matches:
            top_matches.append(first_topic)

    # Map back to original casing
    original_topic_map = {t.lower(): t for t in topics}
    return [original_topic_map.get(t, t) for t in top_matches]

@app.route("/options", methods=["GET"])
def get_options():
    """
    Returns the list of universities and their departments for dropdowns.
    Uses DISPLAY_NAME_MAP for the visible name, keeps 'slug' as the folder name.
    """
    payload = list_universities_and_departments()  # currently returns name=slug=folder
    for uni in payload.get("universities", []):
        slug = uni.get("slug") or uni.get("name")
        uni["slug"] = slug
        uni["name"] = DISPLAY_NAME_MAP.get(slug, slug)
    return jsonify(payload)

@app.route("/find-professors", methods=["POST"])
def find_professors():
    """
    Body:
      {
        "university": "Caltech",                     # folder name under /Faculty
        "department": "caltech_computer_science",    # filename (without .csv)
        "max": 50                                     # optional limit
      }
    """
    payload = request.get_json(silent=True) or {}
    uni = payload.get("university", "").strip()
    dept_slug = payload.get("department", "").strip()
    limit = int(payload.get("max", 50))

    if not uni or not dept_slug:
        return jsonify({"error": "Both 'university' and 'department' are required"}), 400

    # Validate existence
    uni_dir = FACULTY_DIR / uni
    csv_path = uni_dir / f"{dept_slug}.csv"
    if not uni_dir.exists() or not csv_path.exists():
        return jsonify({"error": "University or department not found"}), 404

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[ERROR] Reading CSV failed: {e}")
        return jsonify({"error": "Failed to read department CSV"}), 500

    # normalize columns
    df.columns = [c.strip().lower() for c in df.columns]

    # Expect at least name/title columns; email may be missing or obfuscated
    name_col = next((c for c in df.columns if c in ("name", "full name", "professor", "professor_name")), None)
    title_col = next((c for c in df.columns if c in ("title", "position", "role")), None)
    email_col = next((c for c in df.columns if "email" in c), None)

    if not name_col:
        return jsonify({"error": "CSV missing a 'name' column"}), 500
    if not title_col:
        title_col = None  # optional

    results = []
    for _, row in df.iterrows():
        name = str(row.get(name_col, "")).strip()
        if not name:
            continue

        title = str(row.get(title_col, "")).strip() if title_col else ""
        raw_email = str(row.get(email_col, "")).strip() if email_col else ""

        # Accept only clearly valid emails from CSV
        email = is_valid_email_text(raw_email)
        # if not email:
        #     email = find_email_online(name, uni)
        
        if email and email != "Not Available":
            remember_email(name, uni, email)
            # optional CSV persistence:
            write_back_email_to_csv(uni, dept_slug, name, email)

        prof_id = get_openalex_id_for_prof(name, uni)

        # Fallback CSV-based ID if OpenAlex didn't resolve
        if not prof_id:
            prof_id = f"csv::{uni}::{dept_slug}::{_slugify_name(name)}"

        results.append({
            "id": prof_id,  # now guaranteed non-empty
            "name": name,
            "title": title,
            "email": email if email else "Not Available",
            "university": uni,
            "department": dept_slug
        })

        if len(results) >= limit:
            break

    return jsonify({"professors": results})

# =========================================================
# Metrics Utilities
# ========================================================

@app.route("/metrics", methods=["GET"])
def get_metrics():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # Total students connected
    cursor.execute("SELECT COUNT(*) AS total_students FROM users2")
    total_students = cursor.fetchone()["total_students"]
    total_students += 10

    # Faculty contacts
    cursor.execute("SELECT COUNT(*) AS total_faculty FROM user_connections")
    total_faculty = cursor.fetchone()["total_faculty"]

    # Universities covered (distinct universities from user_connections)
    cursor.execute("SELECT COUNT(DISTINCT university) AS total_universities FROM user_connections")
    total_universities = cursor.fetchone()["total_universities"]

    cursor.close()

    return jsonify({
        "students_connected": total_students,
        "faculty_contacts": total_faculty,
        "universities_covered": total_universities
    })



# =========================================================
# NEW ENDPOINT: Professors by School + Field
# =========================================================

@app.route("/gptprofessorsearch", methods=["POST"])
def search_professors():
    """
    Request JSON:
    {
      "school": "Stanford University",
      "field": "Artificial Intelligence"
    }
    Returns JSON with professors, enriched with OpenAlex info and stable IDs.
    """
    try:
        data = request.get_json()
        school = data.get("school", "").strip()
        field = data.get("field", "").strip()

        if not school or not field:
            return jsonify({"error": "Missing 'school' or 'field'"}), 400

        # Step 1: Ask GPT to suggest professors
        gpt_prompt = f"""
        Provide a JSON array of up to 15 professors at {school} who specialize in {field}.
        Each object must have: name, department, and (if available) email.
        If email is unknown, use "Not Available".
        Return valid JSON only.
        """

        gpt_response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You return only clean JSON, no commentary."},
                {"role": "user", "content": gpt_prompt},
            ],
            max_tokens=800,
            temperature=0.3
        )

        raw_text = gpt_response.choices[0].message.content.strip()

        # Step 2: Parse GPT JSON safely
        try:
            prof_list = json.loads(raw_text)
        except Exception:
            # fallback: parse lines but filter invalid entries
            prof_list = []
            for line in raw_text.split("\n"):
                line = line.strip()
                if line and not line.startswith(("N/A", "•", "Quick Email", "Learn More")):
                    prof_list.append({"name": line, "department": field, "email": "Not Available"})

        enriched_professors = []

        for prof in prof_list:
            name = prof.get("name", "").strip()
            dept = prof.get("department", "").strip()
            email = is_valid_email_text(prof.get("email", "")) or "Email Not Available"

            # Step 3: Try to get OpenAlex ID
            oa_id = get_openalex_id_for_prof(name, school)
            # If we got a full URL, extract the short ID
            # Normalize to short ID
            if oa_id.startswith("https://openalex.org/authors/"):
                short_id = oa_id.split("/")[-1]  # "A5086173064"
            elif oa_id.startswith("authors/"):
                short_id = oa_id.split("/")[-1]  # remove the "authors/" prefix
            else:
                short_id = oa_id  # already short ID
            
            oa_id = short_id
            # if oa_id and not oa_id.startswith("http"):
            #     oa_id = f"https://openalex.org/{oa_id}"

            # Step 4: Generate stable fallback ID if OpenAlex fails
            prof_id = oa_id or f"{name.lower().replace(' ', '-')}-{school.lower().replace(' ', '-')}"

            research_areas, recent_papers, biography = [], [], ""

            if oa_id:
                try:
                    author = Authors()[oa_id]
                    if author:
                        xconcepts = author.get("x_concepts") or []
                        research_areas = [c.get("display_name") for c in xconcepts if c.get("display_name")]
                        recent_papers = fetch_recent_papers(oa_id, max_papers=5)
                        biography = author.get("biography") or ""
                except Exception as e:
                    print(f"[WARN] Could not fetch OpenAlex info for {name}: {e}")

            enriched_professors.append({
                "id": prof_id,
                "name": name,
                "department": dept,
                "email": email or "Not Available",
                "university": school,
                "researchAreas": research_areas,
                "recentPapers": recent_papers,
                "biography": biography
            })

        # Step 5: Filter out malformed entries
        enriched_professors = [
            p for p in enriched_professors if p.get("name") and p.get("department")
        ]

        return jsonify({"professors": enriched_professors}), 200

    except Exception as e:
        print(f"[ERROR] /gptprofessorsearch failed: {e}")
        return jsonify({"error": "Failed to fetch professors"}), 500
    
# MySQL Shi ________________________________________________
db = mysql.connector.connect(
    host="maglev.proxy.rlwy.net",   # just the host
    user="root",
    password="FyyPhJFaKtZmvsuGFaoegfzngiQzGYbL",  # your Railway password
    database="railway",
    port=47263                       # from the URL
)
cursor = db.cursor()

def get_db():
    global db
    try:
        db.ping(reconnect=True, attempts=3, delay=2)
    except:
        db = mysql.connector.connect(
            host="maglev.proxy.rlwy.net",   # just the host
            user="root",
            password="FyyPhJFaKtZmvsuGFaoegfzngiQzGYbL",  # your Railway password
            database="railway",
        )
    return db

@app.route("/auth/signup", methods=["POST"])
def signup():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"message": "All fields are required"}), 400

    cursor = db.cursor(dictionary=True)

    # Check if user already exists
    cursor.execute("SELECT id FROM users2 WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        return jsonify({"message": "Email already registered"}), 400

    # Hash the password
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    # Insert into database
    cursor.execute(
        "INSERT INTO users2 (name, email, password_hash, created_at) VALUES (%s, %s, %s, NOW())",
        (name, email, hashed_pw.decode("utf-8"))
    )
    db.commit()
    user_id = cursor.lastrowid

    cursor.close()

    # Create JWT token
    token = jwt.encode(
        {"id": user_id, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)},
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    cursor.close()
    db.close()

    return jsonify({
        "token": token,
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "createdAt": datetime.datetime.utcnow().isoformat()
        }
    })


@app.route("/auth/login", methods=["POST"])
def login():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id, name, email, password_hash FROM users2 WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()

    if not user:
        return jsonify({"message": "Invalid email or password"}), 401

    # Verify password
    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return jsonify({"message": "Invalid email or password"}), 401

    # Create JWT
    token = jwt.encode(
        {"id": user["id"], "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)},
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    cursor.close()
    db.close()

    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"]
        }
    })

#Check login------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]

        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        try:
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = data  # <--- use entire payload
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        return f(current_user=current_user, *args, **kwargs)

    return decorated

@app.route("/user/connections", methods=["GET"])
@token_required
def get_connections(current_user):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM user_connections WHERE user_id = %s ORDER BY date_contacted DESC",
        (current_user['id'],)
    )
    rows = cursor.fetchall()
    cursor.close()

    return jsonify({"connections": rows})


@app.route("/user/connections", methods=["POST"])
@token_required  # middleware to check JWT and attach user info
def add_connection(current_user):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    data = request.get_json()
    professor_name = data.get("professorName")
    university = data.get("university")
    email = data.get("email")
    field = data.get("field")

    cursor.execute(
        "INSERT INTO user_connections (user_id, professor_name, university, email, field) VALUES (%s, %s, %s, %s, %s)",
        (current_user['id'], professor_name, university, email, field)
    )
    db.commit()
    cursor.close()

    return jsonify({"message": "Professor saved successfully"}), 201

@app.route("/user/connections/<int:connection_id>", methods=["PATCH"])
@token_required
def update_connection_status(current_user, connection_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)
    data = request.get_json()
    status = data.get("status")

    if status not in ("pending", "responded", "no_response"):
        return jsonify({"error": "Invalid status"}), 400

    cursor.execute(
        "UPDATE user_connections SET status = %s WHERE id = %s AND user_id = %s",
        (status, connection_id, current_user['id'])
    )
    db.commit()
    cursor.close()

    return jsonify({"message": "Status updated successfully"})

@app.route("/user/connections/<int:connection_id>", methods=["DELETE"])
@token_required
def delete_connection(current_user, connection_id):
    db = get_db()
    cursor = db.cursor()
    
    # Ensure the user owns this connection
    cursor.execute(
        "DELETE FROM user_connections WHERE id = %s AND user_id = %s",
        (connection_id, current_user['id'])
    )
    
    db.commit()
    cursor.close()
    
    return jsonify({"message": "Connection deleted successfully"}), 200





# -------------------------------

@app.route("/", methods=["GET"])
def root():
    return "Backend is alive!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)
