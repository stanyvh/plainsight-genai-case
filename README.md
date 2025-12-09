# Plainsight GenAI Case

Pipeline that processes PDF documents stored in Azure Blob Storage, extracts key metadata using Azure OpenAI, and upserts the structured results into Azure Cosmos DB.

## Data flow
- List blobs in `plainsightgenaicase` container.
- For each PDF: download bytes, compute a stable document id (filename + SHA-256 digest), and extract page text with `pypdf`.
- Send the text to the `gpt-5-chat` Azure OpenAI deployment for field extraction (architect, client, date, address, confidence).
- Upsert the extracted data into Cosmos DB (`LastenboekenDb` / `LastenboekenDbContainer`).

## Requirements
- Python 3.10+
- Access to Azure resources: Blob Storage, Cosmos DB, Azure OpenAI deployment.
- Recommended: virtual environment for dependencies.

## Setup
1) Create and activate a virtual environment (optional but recommended).
2) Install dependencies:
```bash
pip install -r requirements.txt
```
3) Provide environment variables (see below). You can copy `.env` from secure storage and avoid committing secrets.

## Environment variables
Create a `.env` file or export these variables before running:
```bash
AZURE_STORAGE_CONNECTION_STRING="..."  # connection string for the storage account
AZURE_STORAGE_CONTAINER=plainsightgenaicase
COSMOS_ENDPOINT="..."                  # e.g., https://<account>.documents.azure.com:443/
COSMOS_KEY="..."                       # primary or secondary key
COSMOS_DATABASE=LastenboekenDb
COSMOS_CONTAINER=LastenboekenDbContainer
OPENAI_ENDPOINT="..."                 # Azure OpenAI endpoint
OPENAI_API_KEY="..."                  # Azure OpenAI API key
```

## Running the pipeline
```bash
python main.py
```
The script prints progress for each blob and upserts Cosmos DB items with the computed document id.

## Utility scripts / tests
- `python tests/azureopenai_connection_test.py` — quick connectivity check to Azure OpenAI.
- `python tests/check_content_cosmosdb.py` — list sample documents and fields from the Cosmos container.

## Notes
- The pipeline only processes PDF blobs. Other file types are skipped.
- Document ids are deterministic; re-processing the same file produces the same id.
- Keep secrets out of version control. Rotate keys if a checked-in `.env` contains live credentials.
