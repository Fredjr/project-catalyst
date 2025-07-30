# Project Catalyst: Investigator Discovery Platform

🔬 **A comprehensive full-stack platform for discovering and ranking clinical trial investigators using live biomedical data sources.**

## 🎯 Overview

Project Catalyst is an intelligent investigator discovery engine that helps pharmaceutical and biotech companies identify top clinical trial investigators for specific therapeutic areas. The platform integrates real-time data from PubMed, Semantic Scholar, and ClinicalTrials.gov to provide transparent, data-driven investigator rankings.

### ✨ Key Features

- **🔍 Intelligent Discovery**: Batch discovery of investigator candidates from PubMed literature
- **📊 Dual Scoring System**: Scholar Score (publications + citations) + Operator Score (clinical trials)
- **🌐 Live Data Integration**: Real-time API calls to major biomedical databases
- **🎨 Modern Web Interface**: Responsive dashboard with interactive results
- **🔬 Transparency Features**: Detailed data source information for each investigator
- **⚡ Fast API Backend**: RESTful FastAPI server with CORS support

## 🏗️ Architecture

### Backend Components
- **FastAPI Server** (`api_main.py`): RESTful API with investigator discovery endpoint
- **Data Connectors**: PubMed, Semantic Scholar, and ClinicalTrials.gov integrations
- **Scoring Engines**: Scholar Score and Operator Score algorithms
- **Batch Processing**: Candidate discovery and profile generation pipeline

### Frontend Components
- **Single Page Application**: Modern HTML5 + Tailwind CSS + Vanilla JavaScript
- **Interactive Dashboard**: Search interface with real-time results
- **Transparency Modal**: Detailed data source information for each investigator
- **Responsive Design**: Mobile-first approach with smooth animations

### Data Sources
- **PubMed E-utilities API**: Publication discovery and metadata
- **Semantic Scholar Graph API**: Citation counts and impact metrics
- **ClinicalTrials.gov API v2**: Clinical trial data and investigator roles

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd molecule_api
```

2. **Create and activate virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Unix/macOS
# or
venv\Scripts\activate  # On Windows
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

### Running the Application

1. **Start the backend API server**:
```bash
source venv/bin/activate
uvicorn api_main:app --reload --port 8002
```

2. **Start the frontend server** (in a new terminal):
```bash
python -m http.server 3000
```

3. **Access the application**:
   - Frontend Dashboard: http://127.0.0.1:3000
   - Backend API: http://127.0.0.1:8002
   - API Documentation: http://127.0.0.1:8002/docs

## 📖 Usage

### Web Interface
1. Open the dashboard at http://127.0.0.1:3000
2. Enter a search query (e.g., "KRAS G12C lung cancer", "immunotherapy melanoma")
3. View ranked investigator results with scores
4. Click the info icon on any card to see data source details

### API Usage

**Endpoint**: `POST /find-investigators/`

**Request**:
```json
{
  "query": "KRAS G12C lung cancer"
}
```

**Response**:
```json
[
  {
    "investigatorId": "pid_john_doe",
    "name": "John Doe",
    "affiliation": "Harvard Medical School",
    "scores": {
      "scholar": 8.5,
      "operator": 6.2,
      "overall": 7.4
    },
    "publicationCount": 12,
    "trialCount": 3
  }
]
```

## 🧮 Scoring Methodology

### Scholar Score (0-10)
- **Publication Recency**: Weighted by publication date (recent = higher weight)
- **Citation Impact**: Logarithmic scaling of citation counts
- **Formula**: `recency_weight * log2(citations + 1) * 2.0`

### Operator Score (0-10)
- **Trial Experience**: Based on number and complexity of trials led
- **Success Rate**: Ratio of completed vs. terminated trials
- **Formula**: `(experience_score * 0.7) + (success_rate * 0.3)`

### Overall Score
- **Combined Average**: `(Scholar Score + Operator Score) / 2`
- **Ranking**: Investigators sorted by Overall Score (descending)

## 📁 Project Structure

```
molecule_api/
├── api_main.py              # FastAPI backend server
├── index.html               # Frontend dashboard
├── requirements.txt         # Python dependencies
├── README.md               # This documentation
├── venv/                   # Virtual environment
├── __pycache__/            # Python cache files
└── legacy_files/           # Previous development iterations
    ├── pubmed_connector.py
    ├── clinicaltrials_connector.py
    ├── semantic_scholar_connector.py
    └── batch_processor_engine_v1.py
```

## 🔧 Development

### Core Components

1. **Data Schemas** (`api_main.py`):
   - `Publication`: PubMed article metadata
   - `Trial`: Clinical trial information
   - `Investigator`: Complete investigator profile

2. **API Endpoints**:
   - `POST /find-investigators/`: Main discovery endpoint
   - `GET /`: Health check
   - `GET /health`: Detailed health status

3. **Frontend Features**:
   - Search interface with validation
   - Loading states and error handling
   - Investigator cards with score visualization
   - Transparency modal with data source details

### Adding New Features

1. **New Scoring Pillars**: Add functions to `api_main.py` and update the `Investigator` profile
2. **Additional Data Sources**: Create new connector functions following existing patterns
3. **UI Enhancements**: Modify `index.html` with new components and styling

## 🔒 Security & Production

### Current Configuration
- **CORS**: Wide open for development (`allow_origins=["*"]`)
- **API Keys**: No authentication required for external APIs
- **Rate Limiting**: Basic delays between API calls

### Production Recommendations
- Restrict CORS to specific domains
- Implement API key management for external services
- Add authentication and authorization
- Set up proper logging and monitoring
- Use environment variables for configuration

## 🧪 Testing

### Sample Queries
- "KRAS G12C lung cancer"
- "immunotherapy melanoma"
- "CAR-T cell therapy"
- "Alzheimer's disease"
- "breast cancer HER2"

### Expected Behavior
- Returns 1-10 ranked investigators
- Each investigator has scores 0-10
- Publication and trial counts are accurate
- Modal shows transparent data source information

## 📊 Performance

- **Average Response Time**: 15-30 seconds (due to multiple API calls)
- **Candidate Discovery**: 10-15 investigators per query
- **Final Results**: Top 10 ranked investigators
- **API Rate Limits**: Respectful delays to avoid blocking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is proprietary and confidential.

## 🆘 Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review the console logs for debugging
3. Ensure all external APIs are accessible
4. Verify virtual environment activation

---

**Built with ❤️ for the pharmaceutical and biotech research community**
