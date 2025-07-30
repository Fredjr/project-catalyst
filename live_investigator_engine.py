"""
Project Catalyst - Live Investigator Profile Engine
Phase 2, Task 2: Complete End-to-End Live Data Pipeline

This script creates complete investigator profiles using live API calls to:
- PubMed (publications)
- Semantic Scholar (citations)
- ClinicalTrials.gov (trials)
- Real-time scoring algorithms
"""

import json
import time
import requests
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import math
from collections import defaultdict

# --- CONFIGURATION ---
NCBI_API_KEY = None
SEMANTIC_SCHOLAR_API_KEY = None
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/"
CTGOV_API_BASE_URL = "https://clinicaltrials.gov/api/v2/"

# --- DATA SCHEMAS ---
@dataclass
class Publication:
    publicationId: str; title: str; journal: str; publicationDate: str; authors: List[str]; sourceUrl: str; citationCount: Optional[int] = None

@dataclass
class Trial:
    trialId: str; title: str; status: str; phase: str; startDate: Optional[str]; primaryCompletionDate: Optional[str]; enrollmentCount: Optional[int]; sourceUrl: str

@dataclass
class Investigator:
    investigatorId: str; name: str; affiliation: str; publications: List[Publication]; trials: List[Trial]; scores: dict

# --- LIVE DATA ENGINES (from previous steps) ---
def fetch_and_process_publications(full_name: str, affiliation: str) -> List[Publication]:
    """Fetches and processes publication data for a single PI."""
    # This function remains the same as in the previous version
    search_term = f"{full_name}[Author] AND {affiliation}[Affiliation]"
    esearch_params = {"db": "pubmed", "term": search_term, "retmode": "json", "retmax": "10", "sort": "pub_date"}
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
    # This function remains the same as in the previous version
    search_expression = f"AREA[OverallOfficialName] {full_name}"
    params = {"query.term": search_expression, "format": "json", "pageSize": 25}
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

# --- SCORING ENGINES (from previous steps) ---
def calculate_scholar_score(publications: List[Publication]) -> dict:
    # This function remains the same
    if not publications: return {"final_score": 0}
    today = datetime.now()
    recency_points = sum(1.0 if (today - datetime.strptime(p.publicationDate, "%Y-%m-%d")).days <= 730 else 0.5 for p in publications)
    recency_score = (recency_points / len(publications)) * 10
    total_citations = sum(p.citationCount for p in publications if p.citationCount is not None)
    impact_score = min(10.0, math.log(total_citations + 1, 1.5))
    return {"final_score": round((recency_score * 0.6) + (impact_score * 0.4), 1)}

def calculate_operator_score(trials: List[Trial]) -> dict:
    # This function remains the same
    if not trials: return {"final_score": 0}
    exp_points = sum(1.5 if "Phase 3" in t.phase else 1.0 if "Phase 2" in t.phase else 0.75 for t in trials)
    experience_score = min(10.0, math.log2(exp_points + 1) * 2.0)
    completed = sum(1 for t in trials if t.status.upper() == "COMPLETED")
    terminated = sum(1 for t in trials if t.status.upper() == "TERMINATED")
    success_rate = 5.0 if (completed + terminated) == 0 else max(0, (completed - (terminated * 1.5)) / (completed + terminated)) * 10
    return {"final_score": round((experience_score * 0.7) + (success_rate * 0.3), 1)}

# --- NEW: BATCH PROCESSING AND DISCOVERY ENGINE ---
def discover_pi_candidates(query: str, max_candidates: int = 15) -> List[Dict[str, str]]:
    """
    Discovers potential PI candidates from a search query by finding authors of relevant papers.
    """
    print(f"--- Discovering PI candidates for query: '{query}' ---")
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
            
            name_node = first_author.find('LastName')
            initials_node = first_author.find('ForeName')
            if name_node is None or initials_node is None: continue
            name = f"{initials_node.text} {name_node.text}"
            
            affiliation_node = first_author.find('.//AffiliationInfo/Affiliation')
            affiliation = affiliation_node.text if affiliation_node is not None else 'N/A'
            
            candidates[name]['count'] += 1
            if candidates[name]['affiliation'] == 'N/A':
                candidates[name]['affiliation'] = affiliation

        # Return the most frequently appearing authors as candidates
        sorted_candidates = sorted(candidates.items(), key=lambda item: item[1]['count'], reverse=True)
        return [{"name": name, "affiliation": data['affiliation']} for name, data in sorted_candidates[:max_candidates]]
    except Exception as e:
        print(f"Error during candidate discovery: {e}")
        return []

def find_top_investigators(query: str, top_n: int = 10) -> List[Investigator]:
    """
    Main orchestration function to find and rank top investigators for a given query.
    """
    candidates = discover_pi_candidates(query)
    if not candidates:
        print("Could not find any potential investigators.")
        return []

    print(f"\n--- Processing {len(candidates)} discovered candidates ---")
    all_profiles = []
    for i, candidate in enumerate(candidates):
        print(f"\nProcessing Candidate {i+1}/{len(candidates)}: {candidate['name']}")
        # Simplified profile creation for batch mode to avoid excessive API calls
        publications = fetch_and_process_publications(candidate['name'], candidate['affiliation'])
        trials = fetch_and_process_trials(candidate['name'])
        
        if not publications and not trials:
            print(f"  > No data found for {candidate['name']}. Skipping.")
            continue
            
        scholar_score = calculate_scholar_score(publications)
        operator_score = calculate_operator_score(trials)
        
        profile = Investigator(
            investigatorId=f"pid_{candidate['name'].replace(' ', '_').lower()}",
            name=candidate['name'],
            affiliation=candidate['affiliation'],
            publications=publications,
            trials=trials,
            scores={
                "scholar": scholar_score['final_score'],
                "operator": operator_score['final_score'],
                "overall": round((scholar_score['final_score'] + operator_score['final_score']) / 2, 1)
            }
        )
        all_profiles.append(profile)

    # Rank all processed profiles by their overall score
    print("\n--- Ranking all processed profiles ---")
    ranked_profiles = sorted(all_profiles, key=lambda p: p.scores['overall'], reverse=True)

    return ranked_profiles[:top_n]


if __name__ == '__main__':
    search_query = "KRAS G12C lung cancer"
    
    # Run the new batch processing engine
    top_investigators = find_top_investigators(search_query)

    if top_investigators:
        print(f"\n--- TOP {len(top_investigators)} INVESTIGATORS for '{search_query}' ---")
        class DataclassEncoder(json.JSONEncoder):
            def default(self, o):
                if hasattr(o, '__dataclass_fields__'): return {k: v for k, v in o.__dict__.items() if k not in ['publications', 'trials']}
                return super().default(o)
        
        # Print a summary of the top investigators
        print(json.dumps(top_investigators, indent=2, cls=DataclassEncoder))
