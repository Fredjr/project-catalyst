"""
Project Catalyst - Integrated Investigator Profile Engine
Phase 2, Task 1: Complete PI Scorecard Assembly

This script orchestrates all our data connectors and scoring engines to create
complete, unified investigator profiles with Scholar and Operator scores.
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional

# --- Import all our previously built components ---
# For simplicity in this single file, we'll copy the necessary functions.
# In a real application, these would be in separate files and imported.

# From: publication_engine
@dataclass
class Publication:
    publicationId: str
    title: str
    journal: str
    publicationDate: str
    authors: List[str]
    sourceUrl: str
    citationCount: Optional[int] = None

# From: clinicaltrials_connector
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

# From: scholar_score_engine
def calculate_scholar_score(publications: List[Publication]) -> dict:
    """
    Calculates a PI's Scholar Score based on their publication history.
    This function would be imported. For now, we'll use a placeholder.
    In a real run, it would contain the full calculation logic.
    """
    if not publications:
        return {"recency_score": 0, "impact_score": 0, "final_score": 0}
    
    # A simplified mock calculation for this example
    total_citations = sum(p.citationCount for p in publications if p.citationCount is not None)
    recency_score = len(publications) * 1.5  # Mock recency calculation
    impact_score = min(10, total_citations * 0.01)  # Mock impact calculation
    final_score = (recency_score * 0.6) + (impact_score * 0.4)
    
    return {
        "recency_score": round(min(10, recency_score), 1),
        "impact_score": round(impact_score, 1),
        "final_score": round(min(10, final_score), 1)
    }

# From: operator_score_engine
def calculate_operator_score(trials: List[Trial]) -> dict:
    """
    Calculates a PI's Operator Score based on their trial history.
    This function would be imported. For now, we'll use a placeholder.
    """
    if not trials:
        return {"experience_score": 0, "success_rate_score": 0, "final_score": 0}
    
    # A simplified mock calculation for this example
    experience_score = min(10, len(trials) * 1.2)  # Mock experience calculation
    completed = sum(1 for t in trials if t.status.upper() == "COMPLETED")
    success_rate_score = (completed / len(trials)) * 10 if trials else 0
    final_score = (experience_score * 0.7) + (success_rate_score * 0.3)
    
    return {
        "experience_score": round(experience_score, 1),
        "success_rate_score": round(success_rate_score, 1),
        "final_score": round(final_score, 1)
    }

# --- The Main Investigator Schema ---
@dataclass
class Investigator:
    investigatorId: str
    name: str
    affiliation: str
    publications: List[Publication]
    trials: List[Trial]
    scores: dict

# --- The Integrated Engine ---

def create_investigator_profile(full_name: str, affiliation: str) -> Optional[Investigator]:
    """
    Creates a complete, integrated profile for a single investigator.

    This engine orchestrates calls to all our data connectors and scoring algorithms.
    """
    print(f"--- Building Integrated Profile for {full_name} ---")
    
    # In a real application, these would be live API calls to our other engines.
    # For this example, we'll use the sample data we've been working with.
    
    # 1. Fetch and score publications
    print("1. Getting publication history and calculating Scholar Score...")
    # Mock call to publication_engine
    sample_publications_data = [
        {"publicationId": "38428392", "title": "Sample Publication 1", "journal": "Cancer Discov", "publicationDate": "2024-03-01", "authors": ["Pasi A Janne"], "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/38428392/", "citationCount": 5},
        {"publicationId": "34986062", "title": "Sample Publication 2", "journal": "N Engl J Med", "publicationDate": "2022-01-06", "authors": ["Pasi A Janne"], "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/34986062/", "citationCount": 250},
        {"publicationId": "31398308", "title": "Sample Publication 3", "journal": "N Engl J Med", "publicationDate": "2019-08-08", "authors": ["Pasi A Janne"], "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/31398308/", "citationCount": 850},
    ]
    publications_list = [Publication(**data) for data in sample_publications_data]
    scholar_score_results = calculate_scholar_score(publications_list)
    print(f"   > Scholar Score: {scholar_score_results['final_score']}")

    # 2. Fetch and score trials
    print("2. Getting trial history and calculating Operator Score...")
    # Mock call to clinicaltrials_connector
    sample_trials_data = [
        {"trialId": "NCT04685635", "title": "Sample Trial 1", "status": "COMPLETED", "phase": "Phase 2", "startDate": "2021-03-09", "primaryCompletionDate": "2023-12-28", "enrollmentCount": 100, "sourceUrl": "https://clinicaltrials.gov/study/NCT04685635"},
        {"trialId": "NCT03222631", "title": "Sample Trial 2", "status": "COMPLETED", "phase": "Phase 3", "startDate": "2017-10-13", "primaryCompletionDate": "2020-06-15", "enrollmentCount": 300, "sourceUrl": "https://clinicaltrials.gov/study/NCT03222631"},
        {"trialId": "NCT02511106", "title": "Sample Trial 3", "status": "TERMINATED", "phase": "Phase 2", "startDate": "2015-08-01", "primaryCompletionDate": "2017-01-01", "enrollmentCount": 20, "sourceUrl": "https://clinicaltrials.gov/study/NCT02511106"},
    ]
    trials_list = [Trial(**data) for data in sample_trials_data]
    operator_score_results = calculate_operator_score(trials_list)
    print(f"   > Operator Score: {operator_score_results['final_score']}")

    # 3. Assemble the final Investigator object
    print("3. Assembling final integrated profile...")
    
    # Combine scores into a final scorecard
    final_scores = {
        "scholar": {
            "recency_score": scholar_score_results.get('recency_score', 0),
            "impact_score": scholar_score_results.get('impact_score', 0),
            "final_score": scholar_score_results['final_score']
        },
        "operator": {
            "experience_score": operator_score_results.get('experience_score', 0),
            "success_rate_score": operator_score_results.get('success_rate_score', 0),
            "final_score": operator_score_results['final_score']
        },
        # Overall score is a simple average for now
        "overall": round((scholar_score_results['final_score'] + operator_score_results['final_score']) / 2, 1)
    }

    investigator_profile = Investigator(
        investigatorId=f"pid_{full_name.replace(' ', '_').lower()}",
        name=full_name,
        affiliation=affiliation,
        publications=publications_list,
        trials=trials_list,
        scores=final_scores
    )
    
    print("Profile assembly complete.")
    return investigator_profile


if __name__ == '__main__':
    pi_name = "Pasi A. Janne"
    pi_affiliation = "Dana-Farber Cancer Institute"

    # Run the integrated engine
    complete_profile = create_investigator_profile(pi_name, pi_affiliation)

    if complete_profile:
        print("\n--- COMPLETE INTEGRATED INVESTIGATOR PROFILE ---")
        
        # Use a custom encoder to handle dataclasses
        class DataclassEncoder(json.JSONEncoder):
            def default(self, o):
                if hasattr(o, '__dataclass_fields__'):
                    return o.__dict__
                return super().default(o)
        
        print(json.dumps(complete_profile, indent=2, cls=DataclassEncoder))
        
        print("\n--- PI SCORECARD SUMMARY ---")
        print(f"Investigator: {complete_profile.name}")
        print(f"Affiliation: {complete_profile.affiliation}")
        print(f"Publications: {len(complete_profile.publications)}")
        print(f"Clinical Trials: {len(complete_profile.trials)}")
        print(f"Scholar Score: {complete_profile.scores['scholar']['final_score']}/10")
        print(f"Operator Score: {complete_profile.scores['operator']['final_score']}/10")
        print(f"Overall Score: {complete_profile.scores['overall']}/10")
        print("\nNOTE: This is the first complete PI Scorecard from Project Catalyst!")
