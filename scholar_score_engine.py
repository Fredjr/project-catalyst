"""
Project Catalyst - Scholar Score Engine
Phase 1, Task 1: Scholar Score Algorithm

This script calculates a PI's Scholar Score based on their publication history.
The score combines Recency (60% weight) and Impact (40% weight) metrics.
"""

import json
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

# --- DATA SCHEMAS (Imported from our previous work) ---
@dataclass
class Publication:
    publicationId: str
    title: str
    journal: str
    publicationDate: str
    authors: List[str]
    sourceUrl: str
    citationCount: Optional[int] = None

# --- SCORING ENGINE ---

def calculate_scholar_score(publications: List[Publication]) -> dict:
    """
    Calculates a PI's Scholar Score based on their publication history.

    The Scholar Score is a weighted combination of Recency and Impact.
    - Recency Score (60% weight): Prioritizes recent publications.
    - Impact Score (40% weight): Prioritizes highly-cited publications.

    Args:
        publications: A list of Publication objects for the investigator.

    Returns:
        A dictionary containing the final score and its components.
    """
    if not publications:
        return {"recency_score": 0, "impact_score": 0, "final_score": 0}

    recency_score = _calculate_recency_score(publications)
    impact_score = _calculate_impact_score(publications)

    # Apply weighting
    final_score = (recency_score * 0.6) + (impact_score * 0.4)
    
    # Normalize to a 1-10 scale
    final_score_scaled = round(min(10, final_score), 1)

    return {
        "recency_score": round(recency_score, 1),
        "impact_score": round(impact_score, 1),
        "final_score": final_score_scaled
    }

def _calculate_recency_score(publications: List[Publication]) -> float:
    """Calculates a score based on the publication dates."""
    score = 0
    today = datetime.now()
    
    for pub in publications:
        try:
            pub_date = datetime.strptime(pub.publicationDate, "%Y-%m-%d")
            days_since = (today - pub_date).days
            
            if days_since <= 365 * 2: # Last 2 years
                score += 1.0
            elif days_since <= 365 * 5: # Last 5 years
                score += 0.5
            else: # Older than 5 years
                score += 0.1
        except (ValueError, TypeError):
            continue # Skip if date is malformed
            
    # Normalize score by number of publications to get an average
    return (score / len(publications)) * 10 if publications else 0

def _calculate_impact_score(publications: List[Publication]) -> float:
    """Calculates a score based on citation counts."""
    total_citations = sum(p.citationCount for p in publications if p.citationCount is not None)
    
    # Simple logarithmic scaling to prevent massive outliers from dominating the score.
    # A PI with one paper with 1000 citations shouldn't automatically beat one with 10 papers of 50 citations.
    # We use log base 1.5 to provide a reasonable curve.
    import math
    if total_citations == 0:
        return 0
        
    # This is a simple scaling function. We can make it more sophisticated later.
    # log(1) = 0, log(100) ~ 9, log(1000) ~ 14. Caps at a reasonable level.
    scaled_score = math.log(total_citations + 1, 1.5)
    
    return min(10.0, scaled_score) # Cap the score at 10


if __name__ == '__main__':
    # --- Example Usage ---
    # We'll use a sample of enriched publication data for Dr. Pasi A. Janne
    # This data would normally come from our 'publication_engine' script.
    
    sample_publications_data = [
        {
            "publicationId": "38428392", "title": "Sample Title 1", "journal": "Cancer Discov",
            "publicationDate": "2024-03-01", "authors": ["Pasi A Janne"], "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/38428392/", "citationCount": 5
        },
        {
            "publicationId": "38290111", "title": "Sample Title 2", "journal": "JAMA Oncol",
            "publicationDate": "2024-02-01", "authors": ["Pasi A Janne"], "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/38290111/", "citationCount": 12
        },
        {
            "publicationId": "34986062", "title": "Sample Title 3", "journal": "N Engl J Med",
            "publicationDate": "2022-01-06", "authors": ["Pasi A Janne"], "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/34986062/", "citationCount": 250
        },
        {
            "publicationId": "31398308", "title": "Sample Title 4", "journal": "N Engl J Med",
            "publicationDate": "2019-08-08", "authors": ["Pasi A Janne"], "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/31398308/", "citationCount": 850
        }
    ]

    # Create Publication objects from the sample data
    publications_list = [Publication(**data) for data in sample_publications_data]

    print("--- Calculating Scholar Score for Dr. Pasi A. Janne (sample data) ---")
    scholar_scores = calculate_scholar_score(publications_list)
    
    print("\n--- SCHOLAR SCORE RESULTS ---")
    print(json.dumps(scholar_scores, indent=2))
    print("\nNOTE: This score is the first component of our overall PI Scorecard.")
    
    # Show breakdown for transparency
    print("\n--- SCORING BREAKDOWN ---")
    print(f"Publications analyzed: {len(publications_list)}")
    print(f"Recency Score (60% weight): {scholar_scores['recency_score']}/10")
    print(f"Impact Score (40% weight): {scholar_scores['impact_score']}/10")
    print(f"Final Scholar Score: {scholar_scores['final_score']}/10")
