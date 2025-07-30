"""
Project Catalyst - Operator Score Engine
Phase 1, Task 2: Operator Score Algorithm

This script calculates a PI's Operator Score based on their clinical trial history.
The score combines Experience (70% weight) and Success Rate (30% weight) metrics.
"""

import json
from dataclasses import dataclass
from typing import List, Optional
import math

# --- DATA SCHEMAS (Imported from our previous work) ---
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

# --- SCORING ENGINE ---

def calculate_operator_score(trials: List[Trial]) -> dict:
    """
    Calculates a PI's Operator Score based on their clinical trial history.

    The Operator Score is a weighted combination of Experience and Success Rate.
    - Experience Score (70% weight): Prioritizes a high volume of relevant trial experience.
    - Success Rate Score (30% weight): Rewards a track record of completing trials.

    Args:
        trials: A list of Trial objects for the investigator.

    Returns:
        A dictionary containing the final score and its components.
    """
    if not trials:
        return {"experience_score": 0, "success_rate_score": 0, "final_score": 0}

    experience_score = _calculate_experience_score(trials)
    success_rate_score = _calculate_success_rate_score(trials)

    # Apply weighting
    final_score = (experience_score * 0.7) + (success_rate_score * 0.3)
    
    # Normalize to a 1-10 scale
    final_score_scaled = round(min(10, final_score), 1)

    return {
        "experience_score": round(experience_score, 1),
        "success_rate_score": round(success_rate_score, 1),
        "final_score": final_score_scaled
    }

def _calculate_experience_score(trials: List[Trial]) -> float:
    """Calculates a score based on the volume and phase of trials."""
    score = 0
    for trial in trials:
        # Assign points based on trial phase, as later phases are more complex
        if "Phase 3" in trial.phase:
            score += 1.5
        elif "Phase 2" in trial.phase:
            score += 1.0
        elif "Phase 1" in trial.phase:
            score += 0.75
        else: # Early Phase 1, Observational, etc.
            score += 0.25
            
    # Use logarithmic scaling to reward significant experience without letting
    # a PI with 100 trials completely dwarf one with 30 solid trials.
    # log base 2 gives a nice curve: log2(5)=2.3, log2(10)=3.3, log2(20)=4.3
    scaled_score = math.log2(score + 1) * 2.0 # Multiply by 2 to bring it closer to a 1-10 scale
    
    return min(10.0, scaled_score)

def _calculate_success_rate_score(trials: List[Trial]) -> float:
    """Calculates a score based on the ratio of completed trials."""
    completed_trials = 0
    terminated_trials = 0
    
    for trial in trials:
        # We only consider trials that have a definitive outcome
        if trial.status.upper() == "COMPLETED":
            completed_trials += 1
        elif trial.status.upper() == "TERMINATED":
            terminated_trials += 1
            
    total_considered = completed_trials + terminated_trials
    if total_considered == 0:
        return 5.0 # Return a neutral score if no completed/terminated trials found

    # Calculate success rate, but penalize terminations heavily
    success_rate = (completed_trials - (terminated_trials * 1.5)) / total_considered
    
    # Scale to 0-10
    # A perfect record (100% completed) gets a 10.
    # A 50/50 record gets a score around 2.5
    score = max(0, success_rate) * 10
    
    return score


if __name__ == '__main__':
    # --- Example Usage ---
    # We'll use a sample of trial data for Dr. Pasi A. Janne
    # This data would normally come from our 'clinicaltrials_connector' script.
    
    sample_trials_data = [
        {"trialId": "NCT04685635", "title": "Sample Trial 1", "status": "COMPLETED", "phase": "Phase 2", "startDate": "2021-03-09", "primaryCompletionDate": "2023-12-28", "enrollmentCount": 100, "sourceUrl": "https://clinicaltrials.gov/study/NCT04685635"},
        {"trialId": "NCT04333346", "title": "Sample Trial 2", "status": "COMPLETED", "phase": "Phase 2", "startDate": "2020-07-27", "primaryCompletionDate": "2022-07-29", "enrollmentCount": 60, "sourceUrl": "https://clinicaltrials.gov/study/NCT04333346"},
        {"trialId": "NCT05533427", "title": "Sample Trial 3", "status": "RECRUITING", "phase": "Phase 1", "startDate": "2022-10-03", "primaryCompletionDate": "2025-12-31", "enrollmentCount": 50, "sourceUrl": "https://clinicaltrials.gov/study/NCT05533427"},
        {"trialId": "NCT03222631", "title": "Sample Trial 4", "status": "COMPLETED", "phase": "Phase 3", "startDate": "2017-10-13", "primaryCompletionDate": "2020-06-15", "enrollmentCount": 300, "sourceUrl": "https://clinicaltrials.gov/study/NCT03222631"},
        {"trialId": "NCT02511106", "title": "Sample Trial 5", "status": "TERMINATED", "phase": "Phase 2", "startDate": "2015-08-01", "primaryCompletionDate": "2017-01-01", "enrollmentCount": 20, "sourceUrl": "https://clinicaltrials.gov/study/NCT02511106"},
        {"trialId": "NCT01963215", "title": "Sample Trial 6", "status": "COMPLETED", "phase": "Phase 1", "startDate": "2013-10-01", "primaryCompletionDate": "2016-12-01", "enrollmentCount": 45, "sourceUrl": "https://clinicaltrials.gov/study/NCT01963215"}
    ]

    # Create Trial objects from the sample data
    trials_list = [Trial(**data) for data in sample_trials_data]

    print("--- Calculating Operator Score for Dr. Pasi A. Janne (sample data) ---")
    operator_scores = calculate_operator_score(trials_list)
    
    print("\n--- OPERATOR SCORE RESULTS ---")
    print(json.dumps(operator_scores, indent=2))
    print("\nNOTE: This score is the second component of our overall PI Scorecard.")
    
    # Show breakdown for transparency
    print("\n--- SCORING BREAKDOWN ---")
    print(f"Trials analyzed: {len(trials_list)}")
    print(f"Experience Score (70% weight): {operator_scores['experience_score']}/10")
    print(f"Success Rate Score (30% weight): {operator_scores['success_rate_score']}/10")
    print(f"Final Operator Score: {operator_scores['final_score']}/10")
    
    # Additional analytics
    completed = sum(1 for t in trials_list if t.status.upper() == "COMPLETED")
    terminated = sum(1 for t in trials_list if t.status.upper() == "TERMINATED")
    recruiting = sum(1 for t in trials_list if t.status.upper() == "RECRUITING")
    
    print(f"\n--- TRIAL STATUS BREAKDOWN ---")
    print(f"Completed: {completed}")
    print(f"Terminated: {terminated}")
    print(f"Currently Recruiting: {recruiting}")
    print(f"Other: {len(trials_list) - completed - terminated - recruiting}")
