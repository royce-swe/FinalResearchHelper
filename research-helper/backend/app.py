# =========================================================
# Imports
# =========================================================

from pathlib import Path
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import pandas as pd
import time
from functools  import lru_cache
from rapidfuzz import fuzz
from pyalex import Institutions, Authors, Works, config
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
from ddgs import DDGS
from openai import OpenAI
import os
import unicodedata
import json
from threading import RLock
import uuid, hashlib  # NEW for metrics


# =========================================================
# Flask App Configuration
# =========================================================

app = Flask(__name__)
app.url_map.strict_slashes = False

# Allow both localhost (dev) and your production site
CORS(app, 
     origins=["http://localhost:5173", "https://researchconnectai.com"],
     supports_credentials=True,
     resources={r"/*": {"origins": ["http://localhost:5173", "https://researchconnectai.com"]}})

# AI -----------------------
# USE THE API key on ur local environment to run the email generator
# run this in the terminal
# export OPENAI_API_KEY="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"


client = OpenAI()

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

@lru_cache(maxsize=1000)
def get_openalex_id_for_prof(name: str, university: str, *, fuzzy_threshold: int = 80) -> str:
    """
    Robust ID finder:
      1) Normalize university name (map acronyms/aliases).
      2) Try filtering Authors by institution ID AND name.
      3) Fallback: search by name only and fuzzy-match institutions.
    Returns '' if not found quickly.
    """
    try:
        t0 = time.time()
        uni_norm = _normalize_uni(university)

        # --- Try to resolve institution ID first
        try:
            insts = list(
                Institutions()
                .search(uni_norm)
                .select(["id", "display_name"])
                .get()
            )
        except Exception:
            insts = []

        if insts:
            inst_id = insts[0].get("id")
            if inst_id:
                try:
                    candidates_iter = (
                        Authors()
                        .filter(**{
                            "last_known_institutions.id": inst_id,
                            "display_name.search": name,
                        })
                        .select(["id", "display_name", "last_known_institutions", "works_count"])
                        .paginate(per_page=25)
                    )
                    best_id, best_score, best_works = "", -1, -1
                    for page in candidates_iter:
                        for a in page:
                            score = _best_inst_match_score(a.get("last_known_institutions", []), uni_norm)
                            works = int(a.get("works_count") or 0)
                            if score > best_score or (score == best_score and works > best_works):
                                best_score, best_works = score, works
                                best_id = (a.get("id") or "").split("/")[-1]
                        if time.time() - t0 > 3.0:  # soft guard
                            break
                    if best_id and best_score >= fuzzy_threshold:
                        return best_id
                except Exception as e:
                    print(f"[WARN] OpenAlex filter-by-inst failed for {name} @ {uni_norm}: {e}")

        # --- Fallback: search by name; fuzzy on institution names
        try:
            candidates_iter = (
                Authors()
                .search(name)
                .select(["id", "display_name", "last_known_institutions", "works_count"])
                .paginate(per_page=40)
            )
            best_id, best_score, best_works = "", -1, -1
            for page in candidates_iter:
                for a in page:
                    score = _best_inst_match_score(a.get("last_known_institutions", []), uni_norm)
                    works = int(a.get("works_count") or 0)
                    if score > best_score or (score == best_score and works > best_works):
                        best_score, best_works = score, works
                        best_id = (a.get("id") or "").split("/")[-1]
                if time.time() - t0 > 5.0:
                    break
            if best_id and best_score >= fuzzy_threshold:
                return best_id
        except Exception as e:
            print(f"[WARN] OpenAlex name-search failed for {name} @ {uni_norm}: {e}")

    except Exception as e:
        print(f"[WARN] get_openalex_id_for_prof unexpected error: {e}")

    return ""

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


# =========================================================
# Email Lookup & Caching
# =========================================================

# def find_email_online(professor_name: str, university_name: str) -> str:
#     """
#     Try multiple DuckDuckGo queries. Uses a persistent cache (email_cache.json)
#     and prefers emails on the university's .edu domain when possible.
#     """
#     # Normalize university for both cache key and query
#     norm_uni = _normalize_uni(university_name)
#     key_str = str((professor_name.lower().strip(), norm_uni.lower().strip()))

#     # 1) Cache hit?
#     cached = EMAIL_CACHE.get(key_str)
#     if cached:
#         return cached

#     # 2) Build queries with normalized uni
#     queries = [
#         f'"{professor_name}" "{norm_uni}" site:.edu email',
#         f'"{professor_name}" "{norm_uni}" faculty site:.edu contact',
#         f'"{professor_name}" "{norm_uni}" professor site:.edu',
#     ]

#     # 3) Prefer domain heuristic (very light)
#     prefer_domain = None
#     tokens = re.findall(r"[A-Za-z]+", norm_uni.lower())
#     if "stanford" in tokens:
#         prefer_domain = "stanford.edu"
#     elif "caltech" in tokens:
#         prefer_domain = "caltech.edu"
#     elif "florida" in tokens and "atlantic" in tokens:
#         prefer_domain = "fau.edu"
#     elif "florida" in tokens and "state" in tokens:
#         prefer_domain = "fsu.edu"
#     elif "central" in tokens and "florida" in tokens:
#         prefer_domain = "ucf.edu"
#     elif "wisconsin" in tokens and ("madison" in tokens or "–madison" in norm_uni.lower()):
#         prefer_domain = "wisc.edu"

#     # 4) Search & scrape
#     for query in queries:
#         print(f'\n🔎 [DEBUG] Starting search for query: {query}')
#         links = search_duckduckgo(query)

#         for link in links:
#             print(f"   → [DEBUG] Checking: {link}")
#             emails = scrape_page(link, prefer_domain=prefer_domain)
#             valid_emails = [
#                 e for e in emails
#                 if not any(x in e.lower() for x in ["example", "support", "noreply"])
#             ]
#             if valid_emails:
#                 best = valid_emails[0]
#                 with EMAIL_CACHE_LOCK:
#                     EMAIL_CACHE[key_str] = best
#                 _save_email_cache()
#                 print(f"✅ [DEBUG] Found valid email: {best}")
#                 return best
#             else:
#                 print("      ⚠️ [DEBUG] No valid emails found on this page.")
#             time.sleep(1)

#     # 5) Nothing found — remember failure to avoid repeated scraping
#     print("❌ [DEBUG] No email found after all queries.")
#     with EMAIL_CACHE_LOCK:
#         EMAIL_CACHE[key_str] = "Not Available"
#     _save_email_cache()
#     return "Not Available"

# ---------------------------------------------

# ---------------- NEW ENDPOINT: fetch recent papers ----------------
def fetch_recent_papers(author_id, max_papers=5):
    """
    Return up to `max_papers` most recent works for an OpenAlex author.
    Accepts either short IDs (e.g., 'A123456789') or full URLs and normalizes to the URL form.
    """
    papers = []
    try:
        # Normalize to full OpenAlex URL (Works filter expects this)
        full_id = str(author_id)
        if not full_id.startswith("http"):
            full_id = f"https://openalex.org/{full_id}"

        works_iter = (
            Works()
            .filter(**{"authorships.author.id": full_id})
            .sort(publication_year="desc")
            .select([
                "title",
                "publication_year",
                "primary_location",
                "cited_by_count",
                "abstract_inverted_index",
            ])
            .paginate(per_page=20)
        )

        for page in works_iter:
            for work in page or []:
                if len(papers) >= max_papers:
                    return papers

                title = work.get("title") or "Untitled"
                year = work.get("publication_year") or "N/A"

                src = ((work.get("primary_location") or {}).get("source") or {})
                journal = src.get("display_name") or "Unknown Journal"

                citations = work.get("cited_by_count") or 0

                # Rebuild abstract from inverted index if present
                abstract_data = work.get("abstract_inverted_index") or {}
                if isinstance(abstract_data, dict) and abstract_data:
                    # words sorted by first position
                    words_sorted = sorted(
                        abstract_data.items(),
                        key=lambda kv: kv[1][0] if kv[1] else 0
                    )
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

            # polite pacing
            time.sleep(0.2)

    except Exception as e:
        print(f"[WARN] Error fetching papers for {author_id}: {e}")

    return papers

# ---------------- NEW ENDPOINT: get professor details by ID ----------------
@app.route("/professors/<prof_id>", methods=["GET"])
def get_professor_details(prof_id):
    try:
        # Normalize OpenAlex IDs to the short form first
        if prof_id.startswith("http"):
            prof_id = prof_id.split("/")[-1]
        elif prof_id.startswith("openalex.org"):
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

            # find row by slugified name
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

            # email (validate + fallback)
            email = is_valid_email_text(raw_email) or "Not Available"

            # Enrich from OpenAlex if we can resolve an ID
            oa_id = get_openalex_id_for_prof(name, uni)  # cached helper
            research_areas = []
            recent_papers = []
            if oa_id:
                try:
                    full_oa_id = oa_id if str(oa_id).startswith("http") else f"https://openalex.org/{oa_id}"
                    author = Authors()[full_oa_id]  # use full URL form for maximum compatibility
                    if author:
                        xconcepts = author.get("x_concepts") or []
                        research_areas = [c.get("display_name") for c in xconcepts if c.get("display_name")]
                        recent_papers = fetch_recent_papers(full_oa_id)  # safe to pass URL form
                    if not research_areas:
                        print(f"[INFO] No x_concepts for {name} ({uni}) — id={oa_id}")
                    if not recent_papers:
                        print(f"[INFO] No recent works for {name} ({uni}) — id={oa_id}")
                except Exception as e:
                    print(f"[WARN] OpenAlex enrich failed for {name} ({uni}) id={oa_id}: {e}")
            else:
                print(f"[INFO] No OpenAlex ID for '{name}' @ '{uni}' (normalized='{_normalize_uni(uni)}')")

            # fallback to CSV research text if no OpenAlex topics
            if not research_areas and csv_research:
                research_areas = [s.strip() for s in re.split(r"[;,]", csv_research) if s.strip()]

            professor_info = {
                "id": prof_id,  # keep csv::... so the page can refresh reliably
                "name": name,
                "email": email if email else "Not Available",
                "university": uni,
                "department": dept_slug,
                "title": title,
                "researchAreas": research_areas,     # populated if possible
                "biography": f"{name} is a faculty member at {uni}.",
                "recentPapers": recent_papers        # populated if possible
            }
            return jsonify(professor_info), 200

        # ---------- Pure OpenAlex ID path ----------
        full_oa_id = prof_id if str(prof_id).startswith("http") else f"https://openalex.org/{prof_id}"
        author = Authors()[full_oa_id]
        if not author:
            return jsonify({"error": "Professor not found"}), 404

        name = author.get("display_name", "Unknown")
        institutions = author.get("last_known_institutions", [])
        university = institutions[0]["display_name"] if institutions else "Unknown Institution"
        works_count = author.get("works_count", 0)
        topics = [concept.get("display_name") for concept in (author.get("x_concepts") or []) if concept.get("display_name")]

        recent_papers = fetch_recent_papers(full_oa_id)  # pass URL form

        if not topics:
            print(f"[INFO] No x_concepts for OpenAlex id={prof_id}")
        if not recent_papers:
            print(f"[INFO] No recent works for OpenAlex id={prof_id}")

        professor_info = {
            "id": prof_id,
            "name": name,
            "email": "Not Available",
            "university": university,
            "department": "Unknown Department",
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


METRICS_FILE = (Path(__file__).resolve().parent / "metrics.json")
METRICS_LOCK = RLock()

def _sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _load_metrics():
    if METRICS_FILE.exists():
        try:
            with open(METRICS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] failed to load metrics: {e}")
    return {
        "students_connected": 0,
        "seen_ids": [],
        "universities_covered": 0,
        "faculty_contacts": 0,
    }

def _save_metrics(m):
    try:
        tmp = METRICS_FILE.with_suffix(".tmp.json")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=2)
        tmp.replace(METRICS_FILE)
    except Exception as e:
        print(f"[WARN] failed to save metrics: {e}")

def _compute_university_and_faculty_counts():
    """Scan Faculty/ and compute totals."""
    uni_count = 0
    faculty_rows = 0
    if FACULTY_DIR.exists():
        for uni_dir in [p for p in FACULTY_DIR.iterdir() if p.is_dir()]:
            csvs = list(uni_dir.glob("*.csv"))
            if csvs:
                uni_count += 1
            for csv_path in csvs:
                try:
                    # Fast: just read one column to count rows
                    df = pd.read_csv(csv_path, usecols=[0])
                    faculty_rows += len(df.index)
                except Exception:
                    # Fallback rough count
                    try:
                        with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
                            faculty_rows += max(sum(1 for _ in f) - 1, 0)
                    except Exception:
                        pass
    return uni_count, max(faculty_rows, 0)

# Initialize metrics on boot
METRICS = _load_metrics()
uc, fc = _compute_university_and_faculty_counts()
METRICS["universities_covered"] = uc
METRICS["faculty_contacts"] = fc
_save_metrics(METRICS)

@app.route("/metrics/visit", methods=["POST"])
def metrics_visit():
    # simple bot filter
    ua = (request.headers.get("User-Agent") or "").lower()
    if any(x in ua for x in ["bot", "spider", "crawl", "monitor"]):
        return jsonify({"ok": True, "counted": False})

    rcid = request.cookies.get("rcid")
    if not rcid:
        rcid = str(uuid.uuid4())

    rcid_hash = _sha(rcid)
    counted = False

    with METRICS_LOCK:
        if rcid_hash not in METRICS.get("seen_ids", []):
            METRICS["seen_ids"].append(rcid_hash)
            METRICS["students_connected"] = int(METRICS.get("students_connected", 0)) + 1
            _save_metrics(METRICS)
            counted = True

    resp = make_response(jsonify({"ok": True, "counted": counted}))
    # 2 years, Lax so it’s sent on same-site navigations/fetch
    resp.set_cookie("rcid", rcid, max_age=60*60*24*730, samesite="Lax")
    return resp

@app.route("/metrics", methods=["GET"])
def get_metrics():
    # Recompute CSV-based numbers for freshness
    uc, fc = _compute_university_and_faculty_counts()
    with METRICS_LOCK:
        METRICS["universities_covered"] = uc
        METRICS["faculty_contacts"] = fc
        students = int(METRICS.get("students_connected", 0))
        _save_metrics(METRICS)
        payload = {
            "students_connected": students,
            "universities_covered": uc,
            "faculty_contacts": fc,
        }
    return jsonify(payload)

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
            if oa_id and not oa_id.startswith("http"):
                oa_id = f"https://openalex.org/{oa_id}"

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


# -------------------------------

@app.route("/", methods=["GET"])
def root():
    return "Backend is alive!"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)
