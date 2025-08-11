# Install required packages:
# pip install pyalex rapidfuzz

import time
import json
from rapidfuzz import fuzz
from pyalex import Institutions, Authors, Works, config

# ========== CONFIGURATION ==========
config.email = "jalenmathis7@gmail.com"
config.max_retries = 3
config.retry_backoff_factor = 0.1
config.retry_http_codes = [429, 500, 503]

student = {
    "name": "Royce Mathis",
    "grade": "Junior",
    "program": "IB",
    "interests": ["machine learning", "computer engineering"],
    "location": "remote",
    "preferred_universities": ["Stanford University", "Harvard University"]
}

FUZZY_MATCH_THRESHOLD = 70  # Match sensitivity for research areas

# -------- Fetch recent papers for a professor --------
def fetch_recent_papers(author_id, max_papers=5):
    papers = []
    try:
        works_iter = Works().filter(
            **{"authorships.author.id": author_id}
        ).sort(publication_year="desc")  # sorting by publication year descending
        works_iter = works_iter.select(
            ["title", "publication_year", "primary_location", "cited_by_count", "abstract_inverted_index"]
        ).paginate(per_page=20)

        for page in works_iter:
            for work in page:
                if len(papers) >= max_papers:
                    return papers

                title = work.get("title", "Untitled")
                year = work.get("publication_year", "N/A")

                primary_location = work.get("primary_location") or {}
                source = primary_location.get("source") or {}
                journal = source.get("display_name", "Unknown Journal")

                citations = work.get("cited_by_count", 0)

                abstract_data = work.get("abstract_inverted_index") or {}
                if abstract_data:
                    abstract = " ".join(
                        word for word, positions in sorted(
                            ((k, v) for k, v in abstract_data.items()),
                            key=lambda x: min(x[1])
                        )
                    )
                else:
                    abstract = "No abstract available."

                papers.append({
                    "title": title,
                    "year": year,
                    "journal": journal,
                    "citations": citations,
                    "abstract": abstract
                })
            time.sleep(0.3)
    except Exception as e:
        print(f"Error fetching papers for {author_id}: {e}")
    return papers

# -------- Fetch professors for a university --------
def fetch_professors(university, max_results=50):
    professors = []
    try:
        insts = list(Institutions().search(university).get())
        if not insts:
            print(f"No institution found for {university}")
            return professors
        inst_id = insts[0]['id']
        print(f"Found institution ID for {university}: {inst_id}")

        authors_iter = (
            Authors()
            .filter(**{"last_known_institutions.id": inst_id, "works_count": ">10"})
            .select(["id", "display_name", "x_concepts", "last_known_institutions", "works_count", "updated_date"])
            .paginate(per_page=100)
        )

        for page in authors_iter:
            for author in page:
                if len(professors) >= max_results:
                    return professors

                institutions = [inst.get('id', '') for inst in author.get('last_known_institutions', [])]
                if inst_id not in institutions:
                    continue

                updated_date = author.get("updated_date", "")
                if updated_date and updated_date < "2010-01-01":
                    continue

                name = author.get("display_name", "")
                topics = [concept["display_name"] for concept in author.get("x_concepts", [])]
                topic_string = ", ".join(topics)

                # ✅ Fuzzy matching with student interests
                if any(fuzz.partial_ratio(interest.lower(), topic.lower()) >= FUZZY_MATCH_THRESHOLD
                       for interest in student['interests'] for topic in topics):
                    recent_papers = fetch_recent_papers(author["id"])

                    professors.append({
                        "name": name,
                        "email": "N/A",
                        "university": inst_id.split('/')[-1],
                        "research_area": topic_string if topic_string else "N/A",
                        "recent_papers": recent_papers
                    })
            time.sleep(0.5)
    except Exception as e:
        print(f"Error fetching professors for {university}: {e}")
    return professors

# -------- Main script --------
if __name__ == "__main__":
    all_professors = []
    seen_names = set()

    for uni in student['preferred_universities']:
        print(f"\n🔎 Searching professors for {uni}...")
        results = fetch_professors(uni)
        for prof in results:
            if prof['name'] not in seen_names:
                seen_names.add(prof['name'])
                all_professors.append(prof)

    # Save results to JSON file
    with open("professors_with_papers.json", "w", encoding='utf-8') as f:
        json.dump(all_professors, f, indent=2, ensure_ascii=False)

    print("\n✅ Finished! Results saved to professors_with_papers.json")
