# Azure Resource Tagger - Backend

FastAPI backend service for discovering, classifying, and tagging Azure resources using LLM.

## Features

- 🔍 **Resource Discovery**: Automatically discover resources across all accessible Azure subscriptions using Azure Resource Graph
- 🤖 **LLM Classification**: Classify resources into a 3-level hierarchy using Azure OpenAI GPT-4
- 💾 **Storage**: Store classifications in Azure Cosmos DB with status tracking
- ✅ **Validation UI Support**: API endpoints for frontend validation and approval workflow
- 🏷️ **Tag Application**: Batch apply approved tags to Azure resources

## Prerequisites

- Python 3.12+
- Azure CLI installed and authenticated (`az login`)
- Access to Azure subscriptions you want to scan
- Azure OpenAI resource with GPT-4 deployment
- Azure Cosmos DB account (will be auto-created)

## Setup

### 1. Install Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file and set:
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint URL
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `COSMOS_DB_ENDPOINT`: Your Cosmos DB endpoint URL
- `COSMOS_DB_KEY`: Your Cosmos DB primary key

The subscription and tenant IDs are already configured from `az login`.

### 3. Run the Backend

```powershell
# Make sure virtual environment is activated
cd backend

# Run the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 4. API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Discovery & Classification
- `POST /api/resources/discover` - Discover and classify resources
- `GET /api/subscriptions` - List accessible subscriptions

### Resource Management
- `GET /api/resources` - Get all classifications (with filters)
- `GET /api/resources/{resource_id}` - Get specific classification
- `PUT /api/resources/{resource_id}` - Update classification

### Approval Workflow
- `POST /api/resources/approve` - Approve classifications (batch)
- `POST /api/resources/reject` - Reject classifications (batch)
- `POST /api/resources/apply` - Apply all approved tags to Azure

### Statistics
- `GET /api/statistics` - Get classification statistics

## Classification Hierarchy

### Level 1 - Primary Category
- **Infra**: Infrastructure and foundational services
- **Data**: Data storage, processing, and analytics
- **Apps**: Application hosting and runtime

### Level 2 - Subcategory

**Infra**:
- Networking, Compute, Storage, Security, Management, Identity

**Data**:
- Databases, Analytics, Messaging, Cache, DataLake

**Apps**:
- WebApps, Containers, Functions, APIs, AI_ML

### Level 3
- Actual Azure service type (e.g., "Virtual Network", "SQL Database")

## Example Tags Applied

```json
{
  "Workload-L1": "Apps",
  "Workload-L2": "Containers",
  "Workload-L3": "AKS Cluster",
  "Environment": "Production"
}
```

## Development

### Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic data models
│   └── services/
│       ├── __init__.py
│       ├── azure_discovery.py   # Azure Resource Graph queries
│       ├── llm_classifier.py    # OpenAI classification
│       ├── cosmos_db.py         # Cosmos DB operations
│       └── tag_manager.py       # Azure tag application
├── requirements.txt
└── README.md
```

### Testing

```powershell
# Test discovery
curl -X POST http://localhost:8000/api/resources/discover \
  -H "Content-Type: application/json" \
  -d '{}'

# Get all classifications
curl http://localhost:8000/api/resources

# Get statistics
curl http://localhost:8000/api/statistics
```

## Authentication

The backend uses Azure DefaultAzureCredential which supports:
- Azure CLI (`az login`) - for local development
- Managed Identity - for production in Azure
- Environment variables
- Visual Studio Code authentication

Make sure you're logged in with `az login` before running locally.

## Troubleshooting

### "No resources found"
- Ensure you're logged in with `az login`
- Check that you have Reader access to subscriptions
- Verify subscription IDs in the discovery request

### "Azure OpenAI error"
- Verify your OpenAI endpoint and API key in `.env`
- Check that your deployment name matches
- Ensure you have access to the GPT-4 model

### "Cosmos DB connection failed"
- Verify Cosmos DB endpoint and key in `.env`
- Check that the account exists and is accessible
- The database and container will be auto-created

## License

MIT
