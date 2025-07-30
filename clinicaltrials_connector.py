"""
Project Catalyst - ClinicalTrials.gov Data Connector
Phase 0, Task 3: "Glass Box" Data Connector for ClinicalTrials.gov

This script connects to the ClinicalTrials.gov API and fetches trial history for a single investigator.
It provides the "Operator" data pillar to complement our "Scholar" data from PubMed.
"""

import requests
import json
from dataclasses import dataclass
from typing import List, Optional

# --- DATA SCHEMA (as a Python Dataclass for clarity) ---
@dataclass
class Trial:
    trialId: str
    title: str
    status: str
    phase: str
    startDate: Optional[str]
    primaryCompletionDate: Optional[str]
    enrollmentCount: Optional[int]
    sourceUrl: str

# --- CONFIGURATION ---
CTGOV_API_BASE_URL = "https://clinicaltrials.gov/api/v2/"

def fetch_pi_trials(full_name: str) -> List[Trial]:
    """
    Fetches and parses clinical trial data for a single PI from ClinicalTrials.gov.

    This uses the modern v2 API, which returns structured JSON directly.

    Args:
        full_name (str): The full name of the investigator (e.g., "Pasi A Janne").

    Returns:
        A list of Trial objects matching our schema.
    """
    print(f"--- Starting ClinicalTrials.gov search for {full_name} ---")

    # The v2 API uses a search expression. We'll search for the name in the 'OverallOfficialName' field.
    # See API documentation for more fields: https://clinicaltrials.gov/data-api/api-ref
    search_expression = f"AREA[OverallOfficialName] {full_name}"
    
    params = {
        "query.term": search_expression,
        "format": "json",
        "pageSize": 50 # Fetch up to 50 trials
    }

    print(f"1. Searching with expression: '{search_expression}'")
    try:
        response = requests.get(CTGOV_API_BASE_URL + "studies", params=params)
        response.raise_for_status()
        raw_data = response.json()
        print(f"Found {len(raw_data.get('studies', []))} trial records.")
        
        # The parsing happens in the next step
        return parse_ct_gov_json(raw_data)

    except requests.exceptions.RequestException as e:
        print(f"Error during ClinicalTrials.gov API request: {e}")
        return []
    except json.JSONDecodeError:
        print("Error decoding JSON response from API.")
        return []

def parse_ct_gov_json(raw_data: dict) -> List[Trial]:
    """
    Parses the raw JSON from ClinicalTrials.gov into a list of clean Trial objects.

    Args:
        raw_data: The raw dictionary parsed from the API's JSON response.

    Returns:
        A list of Trial objects.
    """
    print("2. Parsing JSON data into structured objects...")
    trials = []
    
    for study in raw_data.get("studies", []):
        protocol = study.get("protocolSection", {})
        
        # Safely extract all the data points, providing default values
        nct_id = protocol.get("identificationModule", {}).get("nctId", "N/A")
        
        trial = Trial(
            trialId=nct_id,
            title=protocol.get("identificationModule", {}).get("officialTitle", "No Title Found"),
            status=protocol.get("statusModule", {}).get("overallStatus", "Unknown"),
            # The 'phases' field is a list, we'll take the first one or default to 'N/A'
            phase=protocol.get("designModule", {}).get("phases", ["N/A"])[0],
            startDate=protocol.get("statusModule", {}).get("startDateStruct", {}).get("date"),
            primaryCompletionDate=protocol.get("statusModule", {}).get("primaryCompletionDateStruct", {}).get("date"),
            enrollmentCount=protocol.get("designModule", {}).get("enrollmentInfo", {}).get("count"),
            sourceUrl=f"https://clinicaltrials.gov/study/{nct_id}"
        )
        trials.append(trial)

    print(f"Successfully parsed {len(trials)} trials.")
    return trials


if __name__ == '__main__':
    # We'll continue using our "Golden Record" PI for testing.
    pi_name = "Pasi A Janne"
    
    # Fetch and parse the trial data
    structured_trials = fetch_pi_trials(pi_name)
    
    if structured_trials:
        print("\n--- PARSED & STRUCTURED OUTPUT (first 2 trials) ---")
        # Pretty print the first two results
        for t in structured_trials[:2]:
            print(json.dumps(t.__dict__, indent=2))
            print("---")
    else:
        print("\nNo trials found for this investigator.")
