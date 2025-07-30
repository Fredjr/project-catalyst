"""
Project Catalyst - PubMed Data Connector with XML Parser
Phase 0, Task 2: "Glass Box" Data Connector for PubMed

This script connects to the PubMed API, fetches publication history for a single investigator,
and parses the raw XML into structured Publication objects matching our schema.
"""

import requests
import json
import time
import xml.etree.ElementTree as ET # Import the XML parsing library

# --- CONFIGURATION ---
# It's highly recommended to get an API key from NCBI to get higher rate limits (from 3 to 10 requests/sec).
# You can get one here: https://www.ncbi.nlm.nih.gov/account/
NCBI_API_KEY = None #@param {type:"string"}

# Base URLs for NCBI E-utilities
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# --- DATA SCHEMA (as a Python Dataclass for clarity) ---
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Publication:
    publicationId: str
    title: str
    journal: str
    publicationDate: str
    authors: List[str]
    sourceUrl: str
    # These will be added later from other APIs
    citationCount: Optional[int] = None

def fetch_pi_publications(full_name: str, affiliation: str = None) -> Optional[str]:
    """
    Fetches raw publication data as an XML string for a single PI from PubMed.
    
    This function performs a two-step process:
    1. ESearch: Searches PubMed for publication IDs (PMIDs) matching the PI's name.
    2. EFetch: Retrieves the detailed records for those PMIDs.

    Args:
        full_name (str): The full name of the investigator (e.g., "Eleanor Vance").
        affiliation (str, optional): The investigator's affiliation to narrow the search. Defaults to None.

    Returns:
        str: Raw XML string containing publication data from PubMed, or None if an error occurs.
    """
    print(f"--- Starting search for {full_name} ---")

    # --- Step 1: ESearch - Find Publication IDs (PMIDs) ---
    # We construct a query term. Including an affiliation makes the search more specific and accurate.
    search_term = f"{full_name}[Author]"
    if affiliation:
        search_term += f" AND {affiliation}[Affiliation]"

    esearch_params = {
        "db": "pubmed",
        "term": search_term,
        "retmode": "json",
        "retmax": "25",  # Reduced for faster testing
        "sort": "pub_date",
    }
    if NCBI_API_KEY:
        esearch_params["api_key"] = NCBI_API_KEY

    print(f"1. Searching PubMed with term: '{search_term}'")
    
    try:
        esearch_response = requests.get(EUTILS_BASE_URL + "esearch.fcgi", params=esearch_params)
        esearch_response.raise_for_status()  # Raises an exception for bad status codes (4xx or 5xx)
        esearch_data = esearch_response.json()
        
        pmid_list = esearch_data.get("esearchresult", {}).get("idlist", [])
        
        if not pmid_list:
            print("No publications found.")
            return None
            
        print(f"Found {len(pmid_list)} publication IDs.")

    except requests.exceptions.RequestException as e:
        print(f"Error during ESearch: {e}")
        return None

    # --- Step 2: EFetch - Retrieve Publication Details ---
    # We take the list of PMIDs and fetch the full details for each.
    pmid_string = ",".join(pmid_list)
    
    efetch_params = {
        "db": "pubmed",
        "id": pmid_string,
        "retmode": "xml", # XML is often more structured and complete than JSON from this legacy API
        "rettype": "abstract",
    }
    if NCBI_API_KEY:
        efetch_params["api_key"] = NCBI_API_KEY

    # NCBI recommends a delay between requests, especially without an API key.
    time.sleep(0.4) 

    print("2. Fetching detailed records...")
    try:
        efetch_response = requests.get(EUTILS_BASE_URL + "efetch.fcgi", params=efetch_params)
        efetch_response.raise_for_status()
        
        print("Successfully fetched publication details.")
        return efetch_response.text

    except requests.exceptions.RequestException as e:
        print(f"Error during EFetch: {e}")
        return None


def parse_pubmed_xml(xml_data: str) -> List[Publication]:
    """
    Parses the raw XML from PubMed into a list of clean Publication objects.

    Args:
        xml_data: A string containing the XML data from the EFetch API call.

    Returns:
        A list of Publication objects, matching our defined schema.
    """
    print("3. Parsing XML data into structured objects...")
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

            publication = Publication(
                publicationId=pmid,
                title=title,
                journal=journal,
                publicationDate=publication_date,
                authors=authors,
                sourceUrl=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            )
            publications.append(publication)
        except Exception as e:
            print(f"Could not parse article with PMID {pmid}. Error: {e}")
            continue

    print(f"Successfully parsed {len(publications)} publications.")
    return publications


if __name__ == '__main__':
    # --- Example Usage ---
    # We'll use a real, highly-published researcher as our "Golden Record" for testing.
    # Dr. Pasi A. Jänne at Dana-Farber Cancer Institute is a leader in lung cancer research.
    pi_name = "Pasi A. Janne"
    pi_affiliation = "Dana-Farber Cancer Institute"
    
    # Step 1 & 2: Fetch raw data
    publication_xml = fetch_pi_publications(pi_name, pi_affiliation)
    
    if publication_xml:
        # Step 3: Parse the data
        structured_publications = parse_pubmed_xml(publication_xml)
        
        print("\n--- PARSED & STRUCTURED OUTPUT (first 2 publications) ---")
        # Pretty print the first two results
        for pub in structured_publications[:2]:
            print(json.dumps(pub.__dict__, indent=2))
            print("---")
