import requests
from typing import Dict, Optional, List
from urllib.parse import quote
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class PubChemAPIError(Exception):
    """Custom exception for PubChem API errors"""
    pass

def fetch_compound_properties(base_url: str, cid: int, molecule_name: str) -> Dict[str, str]:
    """Helper function to fetch compound properties from PubChem"""
    properties_url = f"{base_url}/compound/cid/{cid}/property/IUPACName,MolecularFormula,Title/JSON"
    try:
        properties_response = requests.get(properties_url)
        properties_response.raise_for_status()
        properties_data = properties_response.json()
        
        if "PropertyTable" not in properties_data or "Properties" not in properties_data["PropertyTable"]:
            raise PubChemAPIError(f"No property data found for molecule '{molecule_name}'")
            
        prop = properties_data["PropertyTable"]["Properties"][0]
        name = prop.get("Title", molecule_name)
        iupac_name = prop.get("IUPACName", "IUPAC name not available")
        return {"name": name, "iupac_name": iupac_name}
    except requests.RequestException as e:
        error_msg = f"Error fetching properties for molecule '{molecule_name}': {str(e)}"
        logger.error(error_msg)
        raise PubChemAPIError(error_msg)

def get_pubchem_data(molecule_name: str) -> Dict[str, str]:
    """
    Fetch molecule data from PubChem API using PUG REST.
    
    Args:
        molecule_name (str): Name of the molecule to search for
        
    Returns:
        Dict[str, str]: Dictionary containing:
            - name: Common name (Title)
            - iupac_name: IUPAC name
            - family: Compound class/category
            - mechanism_of_action: Pharmacological action
            
    Raises:
        PubChemAPIError: If API request fails or molecule is not found
    """
    base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    try:
        logger.info(f"Starting PubChem search for molecule: {molecule_name}")
        
        # Clean and encode the molecule name
        molecule_name = molecule_name.strip()
        
        # Try different case variations for better matching
        name_variations = [
            molecule_name,  # Original
            molecule_name.lower(),  # lowercase
            molecule_name.upper(),  # UPPERCASE
            molecule_name.title(),   # Title Case
            molecule_name.replace(' ', '')  # No spaces
        ]
        
        logger.info(f"Will try variations: {name_variations}")
        
        cid = None
        for name in name_variations:
            try:
                # Search for the compound by name to get its CID
                encoded_name = quote(name)
                search_url = f"{base_url}/compound/name/{encoded_name}/cids/JSON"
                logger.info(f"Trying URL: {search_url}")
                
                response = requests.get(search_url)
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Response data: {data}")
                    if "IdentifierList" in data and data["IdentifierList"].get("CID"):
                        cid = data["IdentifierList"]["CID"][0]
                        logger.info(f"Found CID: {cid}")
                        break
                    else:
                        logger.warning(f"No CID found in response for {name}")
                        continue
                
                # If direct name search fails, try alternative methods
                if response.status_code == 404:
                    logger.warning(f"Name search failed for {name}, trying alternative methods")
                    
                    # Try compound search first
                    logger.info(f"Trying compound search for: {name}")
                    search_url = f"{base_url}/compound/fastformula/{encoded_name}/cids/JSON"
                    comp_response = requests.get(search_url)
                    
                    if comp_response.status_code == 200:
                        comp_data = comp_response.json()
                        logger.info(f"Compound search data: {comp_data}")
                        
                        if "IdentifierList" in comp_data and comp_data["IdentifierList"].get("CID"):
                            cid = comp_data["IdentifierList"]["CID"][0]
                            logger.info(f"Found CID through compound search: {cid}")
                            break
                    
                    # Try synonym search as last resort
                    logger.info(f"Trying synonym search for: {name}")
                    search_url = f"{base_url}/compound/name/{encoded_name}/synonyms/JSON"
                    syn_response = requests.get(search_url)
                    
                    if syn_response.status_code == 200:
                        syn_data = syn_response.json()
                        logger.info(f"Synonym data: {syn_data}")
                        
                        if "InformationList" in syn_data and syn_data["InformationList"].get("Information"):
                            info = syn_data["InformationList"]["Information"][0]
                            if "CID" in info:
                                cid = info["CID"]
                                logger.info(f"Found CID through synonym: {cid}")
                                break
                    
            except requests.RequestException as e:
                logger.warning(f"Request failed for {name}: {str(e)}")
                continue
        
        if cid is None:
            suggestions = [
                "Check the spelling of the molecule name",
                "Try using the scientific name (e.g., 'acetylsalicylic acid' instead of 'aspirin')",
                "Try using the chemical formula (e.g., 'C9H8O4' for aspirin')",
                "Remove special characters or try a simpler form of the name"
            ]
            error_msg = f"Molecule '{molecule_name}' not found.\nSuggestions:\n- " + "\n- ".join(suggestions)
            logger.error(error_msg)
            raise PubChemAPIError(error_msg)
        
        # Get compound properties
        logger.info(f"Fetching properties for CID: {cid}")
        properties = fetch_compound_properties(base_url, cid, molecule_name)
            
        # Get classification data
        try:
            classification_url = f"{base_url}/compound/cid/{cid}/classification/JSON"
            classification_response = requests.get(classification_url)
            classification_response.raise_for_status()
            classification_data = classification_response.json()
            
            # Extract family from classification data
            family = "Chemical compound"  # Default classification
            if ("Hierarchies" in classification_data and 
                classification_data["Hierarchies"] and 
                "Taxonomy" in classification_data["Hierarchies"][0]):
                taxonomy = classification_data["Hierarchies"][0]["Taxonomy"]
                if taxonomy:
                    family = taxonomy[-1]["Name"]  # Use the most specific classification
        except Exception as e:
            logger.warning(f"Failed to get classification data: {str(e)}")
            family = "Chemical compound"  # Use default classification
        
        # Get pharmacology data for mechanism of action
        try:
            pharmacology_url = f"{base_url}/compound/cid/{cid}/assaysummary/JSON"
            pharmacology_response = requests.get(pharmacology_url)
            pharmacology_response.raise_for_status()
            pharmacology_data = pharmacology_response.json()
            
            # Extract mechanism of action or use a default message
            mechanism = "Mechanism of action not available"
            if "Table" in pharmacology_data and "Row" in pharmacology_data["Table"]:
                for row in pharmacology_data["Table"]["Row"]:
                    if "Mechanism of Action" in str(row):
                        mechanism = str(row["Description"])
                        break
        except Exception as e:
            logger.warning(f"Failed to get pharmacology data: {str(e)}")
            mechanism = "Mechanism of action not available"
        
        return {
            "name": properties["name"],
            "iupac_name": properties["iupac_name"],
            "family": family,
            "mechanism_of_action": mechanism
        }
            
    except Exception as e:
        error_msg = f"Unexpected error processing molecule '{molecule_name}': {str(e)}"
        logger.error(error_msg)
        raise PubChemAPIError(error_msg)
        
        # Get compound properties
        logger.info(f"Fetching properties for CID: {cid}")
        properties = fetch_compound_properties(base_url, cid, molecule_name)
            
        # Get classification data
        try:
            classification_url = f"{base_url}/compound/cid/{cid}/classification/JSON"
            classification_response = requests.get(classification_url)
            classification_response.raise_for_status()
            classification_data = classification_response.json()
            
            # Extract family from classification data
            family = "Chemical compound"  # Default classification
            if ("Hierarchies" in classification_data and 
                classification_data["Hierarchies"] and 
                "Taxonomy" in classification_data["Hierarchies"][0]):
                taxonomy = classification_data["Hierarchies"][0]["Taxonomy"]
                if taxonomy:
                    family = taxonomy[-1]["Name"]  # Use the most specific classification
        except Exception as e:
            logger.warning(f"Failed to get classification data: {str(e)}")
            family = "Chemical compound"  # Use default classification
        
        # Get pharmacology data for mechanism of action
        try:
            pharmacology_url = f"{base_url}/compound/cid/{cid}/assaysummary/JSON"
            pharmacology_response = requests.get(pharmacology_url)
            pharmacology_response.raise_for_status()
            pharmacology_data = pharmacology_response.json()
            
            # Extract mechanism of action or use a default message
            mechanism = "Mechanism of action not available"
            if "Table" in pharmacology_data and "Row" in pharmacology_data["Table"]:
                for row in pharmacology_data["Table"]["Row"]:
                    if "Mechanism of Action" in str(row):
                        mechanism = str(row["Description"])
                        break
        except Exception as e:
            logger.warning(f"Failed to get pharmacology data: {str(e)}")
            mechanism = "Mechanism of action not available"
        
        return {
            "name": properties["name"],
            "iupac_name": properties["iupac_name"],
            "family": family,
            "mechanism_of_action": mechanism
        }
            
    except Exception as e:
        error_msg = f"Unexpected error processing molecule '{molecule_name}': {str(e)}"
        logger.error(error_msg)
        raise PubChemAPIError(error_msg)
