import json
import time
import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict
from datetime import datetime
import math
from collections import defaultdict

# --- FastAPI Imports ---
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- Initialize FastAPI App ---
app = FastAPI(
    title="Project Catalyst API",
    description="API for discovering and ranking clinical trial investigators.",
    version="1.0.0"
)

# --- CORS Middleware ---
# Allows the frontend (running on a different domain) to communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000", 
        "https://project-catalyst.netlify.app",
        "https://*.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# --- CONFIGURATION & DATA SCHEMAS (from previous steps) ---
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
CTGOV_API_BASE_URL = "https://clinicaltrials.gov/api/v2/"
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/"

@dataclass
class Publication:
    publicationId: str; title: str; journal: str; publicationDate: str; authors: List[str]; sourceUrl: str; citationCount: Optional[int] = None

@dataclass
class Trial:
    trialId: str; title: str; status: str; phase: str; startDate: Optional[str]; primaryCompletionDate: Optional[str]; enrollmentCount: Optional[int]; sourceUrl: str

@dataclass
class Investigator:
    investigatorId: str; name: str; affiliation: str; scores: dict; publicationCount: int; trialCount: int

# --- CORE ENGINE LOGIC (Functions from batch_processor_engine_v1) ---
# Note: These functions are simplified for brevity in this example.
# A production app would import them from other modules.

def fetch_and_process_publications(full_name: str, affiliation: str) -> List[Publication]:
    """Fetches and processes publication data for a single PI."""
    search_term = f"{full_name}[Author] AND {affiliation}[Affiliation]"
    esearch_params = {"db": "pubmed", "term": search_term, "retmode": "json", "retmax": "5", "sort": "pub_date"} # Reduced for API speed
    try:
        esearch_response = requests.get(EUTILS_BASE_URL + "esearch.fcgi", params=esearch_params)
        pmid_list = esearch_response.json().get("esearchresult", {}).get("idlist", [])
        if not pmid_list: return []
        pmid_string = ",".join(pmid_list)
        efetch_params = {"db": "pubmed", "id": pmid_string, "retmode": "xml", "rettype": "abstract"}
        efetch_response = requests.get(EUTILS_BASE_URL + "efetch.fcgi", params=efetch_params)
        xml_data = efetch_response.text
        publications = []
        root = ET.fromstring(xml_data)
        for article_node in root.findall('.//PubmedArticle'):
            pmid = article_node.find('.//PMID').text
            pub = Publication(
                publicationId=pmid,
                title=article_node.find('.//ArticleTitle').text or 'N/A',
                journal=article_node.find('.//Journal/Title').text or 'N/A',
                publicationDate=f"{article_node.find('.//PubDate/Year').text}-01-01",
                authors=[f"{a.find('ForeName').text} {a.find('LastName').text}".strip() for a in article_node.findall('.//AuthorList/Author')],
                sourceUrl=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                citationCount=requests.get(f"{SEMANTIC_SCHOLAR_API_URL}paper/PMID:{pmid}?fields=citationCount").json().get('citationCount', 0)
            )
            publications.append(pub)
            time.sleep(0.4)
        return publications
    except Exception:
        return []

def fetch_and_process_trials(full_name: str) -> List[Trial]:
    """Fetches and processes trial data for a single PI."""
    search_expression = f"AREA[OverallOfficialName] {full_name}"
    params = {"query.term": search_expression, "format": "json", "pageSize": 10}
    try:
        response = requests.get(CTGOV_API_BASE_URL + "studies", params=params)
        raw_data = response.json()
        trials = []
        for study in raw_data.get("studies", []):
            protocol = study.get("protocolSection", {})
            nct_id = protocol.get("identificationModule", {}).get("nctId", "N/A")
            trials.append(Trial(
                trialId=nct_id, title=protocol.get("identificationModule", {}).get("officialTitle", "N/A"),
                status=protocol.get("statusModule", {}).get("overallStatus", "N/A"),
                phase=protocol.get("designModule", {}).get("phases", ["N/A"])[0],
                startDate=protocol.get("statusModule", {}).get("startDateStruct", {}).get("date"),
                primaryCompletionDate=protocol.get("statusModule", {}).get("primaryCompletionDateStruct", {}).get("date"),
                enrollmentCount=protocol.get("designModule", {}).get("enrollmentInfo", {}).get("count"),
                sourceUrl=f"https://clinicaltrials.gov/study/{nct_id}"
            ))
        return trials
    except Exception:
        return []

def calculate_scholar_score(publications: List[Publication]) -> dict:
    if not publications: return {"final_score": 0}
    today = datetime.now()
    recency_points = sum(1.0 if (today - datetime.strptime(p.publicationDate, "%Y-%m-%d")).days <= 730 else 0.5 for p in publications)
    recency_score = (recency_points / len(publications)) * 10
    total_citations = sum(p.citationCount for p in publications if p.citationCount is not None)
    impact_score = min(10.0, math.log(total_citations + 1, 1.5))
    return {"final_score": round((recency_score * 0.6) + (impact_score * 0.4), 1)}

def calculate_operator_score(trials: List[Trial]) -> dict:
    if not trials: return {"final_score": 0}
    exp_points = sum(1.5 if "Phase 3" in t.phase else 1.0 if "Phase 2" in t.phase else 0.75 for t in trials)
    experience_score = min(10.0, math.log2(exp_points + 1) * 2.0)
    completed = sum(1 for t in trials if t.status.upper() == "COMPLETED")
    terminated = sum(1 for t in trials if t.status.upper() == "TERMINATED")
    success_rate = 5.0 if (completed + terminated) == 0 else max(0, (completed - (terminated * 1.5)) / (completed + terminated)) * 10
    return {"final_score": round((experience_score * 0.7) + (success_rate * 0.3), 1)}

def discover_pi_candidates(query: str, max_candidates: int = 10) -> List[Dict[str, str]]:
    """Discovers potential PI candidates from a search query."""
    esearch_params = {"db": "pubmed", "term": query, "retmode": "json", "retmax": str(max_candidates * 2), "sort": "relevance"}
    try:
        response = requests.get(EUTILS_BASE_URL + "esearch.fcgi", params=esearch_params)
        pmids = response.json().get("esearchresult", {}).get("idlist", [])
        if not pmids: return []

        efetch_params = {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"}
        response = requests.get(EUTILS_BASE_URL + "efetch.fcgi", params=efetch_params)
        root = ET.fromstring(response.text)
        
        candidates = defaultdict(lambda: {'count': 0, 'affiliation': 'N/A'})
        for article in root.findall('.//PubmedArticle'):
            author_list = article.find('.//AuthorList')
            if author_list is None: continue
            first_author = author_list.find('.//Author')
            if first_author is None: continue
            name = f"{first_author.find('ForeName').text} {first_author.find('LastName').text}"
            affiliation = (first_author.find('.//AffiliationInfo/Affiliation') or ET.Element("A")).text or 'N/A'
            candidates[name]['count'] += 1
            if candidates[name]['affiliation'] == 'N/A':
                candidates[name]['affiliation'] = affiliation

        sorted_candidates = sorted(candidates.items(), key=lambda item: item[1]['count'], reverse=True)
        return [{"name": name, "affiliation": data['affiliation']} for name, data in sorted_candidates[:max_candidates]]
    except Exception:
        return []

# --- API ENDPOINT ---
class SearchQuery(BaseModel):
    query: str

@app.post("/find-investigators/", response_model=List[Dict])
def find_top_investigators_api(search_query: SearchQuery):
    """
    API endpoint to find and rank top investigators for a given query.
    """
    query = search_query.query
    candidates = discover_pi_candidates(query)
    if not candidates:
        return []

    all_profiles = []
    for candidate in candidates:
        publications = fetch_and_process_publications(candidate['name'], candidate['affiliation'])
        trials = fetch_and_process_trials(candidate['name'])
        
        # Track counts for transparency
        publication_count = len(publications)
        trial_count = len(trials)
        
        if not publications and not trials:
            continue
            
        scholar_score = calculate_scholar_score(publications)
        operator_score = calculate_operator_score(trials)
        
        profile = Investigator(
            investigatorId=f"pid_{candidate['name'].replace(' ', '_').lower()}",
            name=candidate['name'],
            affiliation=candidate['affiliation'],
            scores={
                "scholar": scholar_score['final_score'],
                "operator": operator_score['final_score'],
                "overall": round((scholar_score['final_score'] + operator_score['final_score']) / 2, 1)
            },
            publicationCount=publication_count,
            trialCount=trial_count
        )
        all_profiles.append(asdict(profile))

    ranked_profiles = sorted(all_profiles, key=lambda p: p['scores']['overall'], reverse=True)
    return ranked_profiles[:10]

# --- HEALTH CHECK ENDPOINT ---
@app.get("/")
def read_root():
    return {"message": "Project Catalyst API is running!", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# To run this API:
# 1. Install fastapi and uvicorn: pip install fastapi "uvicorn[standard]"
# 2. Save this file as api_main.py
# 3. Run in your terminal: uvicorn api_main:app --reload
