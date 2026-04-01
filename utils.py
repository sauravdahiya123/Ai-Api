import requests
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from urllib.parse import urljoin, urlparse

model = SentenceTransformer('all-MiniLM-L6-v2')
dimension = 384

user_indexes = {}
user_docs = {}

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ✅ EMBEDDING
def create_embedding(text):
    return model.encode(text)

import pickle , os
def save_index(user_id, index, docs):
    os.makedirs("storage", exist_ok=True)

    faiss.write_index(index, f"storage/{user_id}.index")

    with open(f"storage/{user_id}.pkl", "wb") as f:
        pickle.dump(docs, f)


def load_index(user_id):
    index_path = f"storage/{user_id}.index"
    docs_path = f"storage/{user_id}.pkl"

    if os.path.exists(index_path) and os.path.exists(docs_path):
        index = faiss.read_index(index_path)

        with open(docs_path, "rb") as f:
            docs = pickle.load(f)

        user_indexes[user_id] = index
        user_docs[user_id] = docs

        return index, docs

    return get_index(user_id)

# ✅ GET INDEX
def get_index(user_id):
    if user_id not in user_indexes:
        user_indexes[user_id] = faiss.IndexFlatL2(dimension)
        user_docs[user_id] = []
    return user_indexes[user_id], user_docs[user_id]


# ✅ ADD DATA (with chunking)
def split_text(text, size=500):
    return [text[i:i+size] for i in range(0, len(text), size)]


def add_to_db(user_id, text):
    # index, docs = get_index(user_id)
    index, docs = load_index(user_id)
    chunks = split_text(text)  # 🔥 important

    embeddings = model.encode(chunks)
    print("Save")
    for i, emb in enumerate(embeddings):
        emb = np.array([emb]).astype("float32")
        index.add(emb)
        docs.append(chunks[i])
    save_index(user_id, index, docs)



# ✅ SEARCH (improved)
def search(user_id, query, top_k=5):
    index, docs = load_index(user_id)

    if not docs or index.ntotal == 0:
        return ""

    # 🔥 query boost (important)
    query = query + " explain details working process information"

    q_emb = np.array([create_embedding(query)]).astype("float32")

    D, I = index.search(q_emb, top_k)

    results = []
    for i in I[0]:
        if i == -1:
            continue
        if 0 <= i < len(docs):
            results.append(docs[i])

    return " ".join(results)


# ✅ SCRAPE CLEAN
def scrape(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        # ❌ remove junk
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(" ")
        text = " ".join(text.split())

        return text[:5000]

    except Exception as e:
        print("Scrape error:", url, e)
        return ""


# ✅ GET LINKS
def get_links(base_url):
    links = set()
    try:
        res = requests.get(base_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        for a in soup.find_all("a", href=True):
            full = urljoin(base_url, a["href"])

            if urlparse(full).netloc == urlparse(base_url).netloc:
                links.add(full)

    except Exception as e:
        print("Link error:", e)

    return links


# ✅ FULL CRAWLER (FIXED 🔥)
def crawl_task(user_id, base_url, max_pages=20):
    visited = set()
    to_visit = [base_url]

    count = 0

    while to_visit and count < max_pages:
        url = to_visit.pop(0)

        if url in visited:
            continue

        visited.add(url)

        print("Scraping:", url)

        text = scrape(url)

        if text:
            add_to_db(user_id, text)

        # 🔥 get next links (recursive)
        links = get_links(url)

        for link in links:
            if link not in visited:
                to_visit.append(link)

        count += 1

    print("✅ Total pages scraped:", count)