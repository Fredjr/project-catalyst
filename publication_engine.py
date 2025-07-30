"""
Project Catalyst - Unified Publication Engine
Phase 0, Final Task: Complete "Publication Engine" with Citation Enrichment

This script combines PubMed data fetching with Semantic Scholar citation enrichment
to create a complete Publication data pipeline with impact metrics.
"""

import requests
import json
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Optional

# --- CONFIGURATION ---
# It's highly recommended to get API keys to get higher rate limits.
# NCBI (PubMed): https://www.ncbi.nlm.nih.gov/account/
# Semantic Scholar: https://www.semanticscholar.org/product/api
NCBI_API_KEY = None
SEMANTIC_SCHOLAR_API_KEY = None 

EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
SEMANTIC_SCHOLAR_API_URL = "https://api.semanticscholar.org/graph/v1/"

# --- DATA SCHEMA ---
@dataclass
class Publication:
    publicationId: str
    title: str
    journal: str
    publicationDate: str
    authors: List[str]
    sourceUrl: str
    citationCount: Optional[int] = None

# --- FUNCTIONS ---
def fetch_pi_publications(full_name: str, affiliation: str = None) -> Optional[str]:
    """Fetches raw publication data as an XML string for a single PI from PubMed."""
    print(f"--- Starting PubMed search for {full_name} ---")
    search_term = f"{full_name}[Author]"
    if affiliation:
        search_term += f" AND {affiliation}[Affiliation]"

    esearch_params = {"db": "pubmed", "term": search_term, "retmode": "json", "retmax": "10", "sort": "pub_date"}
    if NCBI_API_KEY: esearch_params["api_key"] = NCBI_API_KEY

    print(f"1. Searching PubMed with term: '{search_term}'")
    try:
        esearch_response = requests.get(EUTILS_BASE_URL + "esearch.fcgi", params=esearch_params)
        esearch_response.raise_for_status()
        pmid_list = esearch_response.json().get("esearchresult", {}).get("idlist", [])
        if not pmid_list:
            print("No publications found.")
            return None
        print(f"Found {len(pmid_list)} publication IDs.")
    except requests.exceptions.RequestException as e:
        print(f"Error during ESearch: {e}")
        return None

    pmid_string = ",".join(pmid_list)
    efetch_params = {"db": "pubmed", "id": pmid_string, "retmode": "xml", "rettype": "abstract"}
    if NCBI_API_KEY: efetch_params["api_key"] = NCBI_API_KEY
    
    time.sleep(0.4)
    print("2. Fetching detailed records from PubMed...")
    try:
        efetch_response = requests.get(EUTILS_BASE_URL + "efetch.fcgi", params=efetch_params)
        efetch_response.raise_for_status()
        print("Successfully fetched publication details.")
        return efetch_response.text
    except requests.exceptions.RequestException as e:
        print(f"Error during EFetch: {e}")
        return None

def fetch_citation_count(pmid: str) -> Optional[int]:
    """Fetches citation count for a given PMID from Semantic Scholar."""
    try:
        headers = {'x-api-key': SEMANTIC_SCHOLAR_API_KEY} if SEMANTIC_SCHOLAR_API_KEY else {}
        # We query the API using the PubMed ID (PMID)
        response = requests.get(
            f"{SEMANTIC_SCHOLAR_API_URL}paper/PMID:{pmid}?fields=citationCount",
            headers=headers
        )
        # Semantic Scholar returns 404 if the paper isn't found
        if response.status_code == 404:
            return 0
        response.raise_for_status()
        data = response.json()
        return data.get('citationCount', 0)
    except requests.exceptions.RequestException as e:
        # Don't stop the whole process for one failed citation lookup
        print(f"Warning: Could not fetch citation count for PMID {pmid}. Error: {e}")
        return None

def parse_and_enrich_publications(xml_data: str) -> List[Publication]:
    """Parses PubMed XML and enriches it with citation data from Semantic Scholar."""
    print("3. Parsing XML and enriching with citation counts...")
    publications = []
    root = ET.fromstring(xml_data)

    for article_node in root.findall('.//PubmedArticle'):
        try:
            pmid_node = article_node.find('.//PMID')
            pmid = pmid_node.text if pmid_node is not None else 'N/A'

            title_node = article_node.find('.//ArticleTitle')
            title = title_node.text if title_node is not None else 'No Title Found'

            journal_node = article_node.find('.//Journal/Title')
            journal = journal_node.text if journal_node is not None else 'No Journal Found'
            
            # Safely extract date components
            pub_date_node = article_node.find('.//PubDate')
            year = pub_date_node.find('Year').text if pub_date_node is not None and pub_date_node.find('Year') is not None else '1900'
            month = pub_date_node.find('Month').text if pub_date_node is not None and pub_date_node.find('Month') is not None else '01'
            day = pub_date_node.find('Day').text if pub_date_node is not None and pub_date_node.find('Day') is not None else '01'
            
            # Convert month abbreviation to number if necessary
            try:
                if month.isalpha():  # Month name like 'Jan', 'Feb'
                    month_num = time.strptime(month, '%b').tm_mon
                else:  # Numeric month
                    month_num = int(month)
            except (ValueError, AttributeError):
                month_num = 1  # Default to January if parsing fails
            
            # Ensure day is numeric
            try:
                day_num = int(day)
            except (ValueError, AttributeError):
                day_num = 1  # Default to 1st if parsing fails
                
            publication_date = f"{year}-{month_num:02d}-{day_num:02d}"

            authors = []
            author_list_node = article_node.find('.//AuthorList')
            if author_list_node is not None:
                for author_node in author_list_node.findall('.//Author'):
                    lastname = author_node.find('LastName').text if author_node.find('LastName') is not None else ''
                    forename = author_node.find('ForeName').text if author_node.find('ForeName') is not None else ''
                    authors.append(f"{forename} {lastname}".strip())

            # Create the base publication object from PubMed data
            pub = Publication(
                publicationId=pmid,
                title=title,
                journal=journal,
                publicationDate=publication_date,
                authors=authors,
                sourceUrl=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            )

            # --- Enrichment Step ---
            # Now, call Semantic Scholar to get the citation count
            print(f"  > Fetching citation count for PMID: {pmid}...")
            time.sleep(0.5) # Adhere to rate limits
            pub.citationCount = fetch_citation_count(pmid)
            
            publications.append(pub)
        except Exception as e:
            print(f"Could not parse or enrich article with PMID {pmid}. Error: {e}")
            continue

    print(f"Successfully processed {len(publications)} publications.")
    return publications

if __name__ == '__main__':
    # We'll continue using our "Golden Record" PI for testing.
    pi_name = "Pasi A Janne"
    pi_affiliation = "Dana-Farber Cancer Institute"
    
    # Fetch raw data from PubMed
    publication_xml = fetch_pi_publications(pi_name, pi_affiliation)
    
    if publication_xml:
        # Parse and enrich the data
        structured_publications = parse_and_enrich_publications(publication_xml)
        
        print("\n--- ENRICHED & STRUCTURED OUTPUT (first 2 publications) ---")
        for pub in structured_publications[:2]:
            print(json.dumps(pub.__dict__, indent=2))
            print("---")
    else:
        print("\nNo publications found for this investigator.")
