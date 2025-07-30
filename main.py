from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pubchem_client import get_pubchem_data, PubChemAPIError
import logging

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(title="Molecule Synthesis API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_root():
    """Serve the scientific dashboard HTML page with no-cache headers"""
    response = FileResponse("static/index.html")
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Define data models for response structure
class TherapeuticInfo(BaseModel):
    indications: str = "Not available"
    conditions: str = "Not available"
    mechanismSimple: str
    mechanismExpert: str = "Not available"

class IdentityInfo(BaseModel):
    commonName: str
    iupacName: str
    pharmacologicalFamily: str
    structureSVG: str = "<div>Structure not available</div>"

class MoleculeResponse(BaseModel):
    identity: IdentityInfo
    therapeutic: TherapeuticInfo

# Hardcoded response data for Aspirin
ASPIRIN_DATA = {
    "identity": {
        "name": "Aspirin",
        "family": "Nonsteroidal anti-inflammatory drug"
    },
    "therapeutic": {
        "mechanism_of_action": "Inhibits prostaglandin synthesis by irreversibly inhibiting both COX-1 and COX-2 enzymes."
    }
}

@app.get("/api/synthesis", response_model=MoleculeResponse)
async def get_synthesis(molecule: str = Query(..., description="Name of the molecule to query")):
    """
    Get synthesis information for a molecule from PubChem API.
    
    Args:
        molecule (str): Name of the molecule to query
    
    Returns:
        MoleculeResponse: Information about the molecule including identity and therapeutic data
    
    Raises:
        HTTPException: If the molecule is not found or if there's an API error
    """
    try:
        logger.debug(f"Received request for molecule: {molecule}")
        
        # Get data from PubChem API
        logger.info(f"Searching PubChem for molecule: {molecule}")
        molecule_data = get_pubchem_data(molecule)
        logger.debug(f"Raw PubChem data: {molecule_data}")
        
        # Transform the data to match our response model
        response_data = {
            "identity": {
                "commonName": molecule_data["name"],
                "iupacName": molecule_data["iupac_name"],
                "pharmacologicalFamily": molecule_data["family"],
                "structureSVG": "<div>Structure not available</div>"
            },
            "therapeutic": {
                "indications": "Not available",
                "conditions": "Not available",
                "mechanismSimple": molecule_data["mechanism_of_action"],
                "mechanismExpert": molecule_data["mechanism_of_action"]
            }
        }
        logger.info(f"Successfully found data for molecule: {molecule}")
        logger.debug(f"Formatted response data: {response_data}")
        return response_data
        
    except PubChemAPIError as e:
        error_msg = str(e)
        logger.error(f"PubChem API error for molecule '{molecule}': {error_msg}")
        raise HTTPException(status_code=404, detail=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error processing molecule '{molecule}': {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
