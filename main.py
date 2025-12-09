import os
import json
import hashlib
from io import BytesIO

from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient
from pypdf import PdfReader
from openai import AzureOpenAI

# ----- LOAD ENVIRONMENT VARIABLES -----
load_dotenv() 

# Environment variables
# Azure Blob Storage
STORAGE_CONNECTION_STRING = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

# Azure Cosmos DB
COSMOS_ENDPOINT = os.environ["COSMOS_ENDPOINT"]
COSMOS_KEY = os.environ["COSMOS_KEY"]
STORAGE_CONTAINER="plainsightgenaicase"
COSMOS_DATABASE="LastenboekenDb"
COSMOS_CONTAINER="LastenboekenDbContainer"

# Azure OpenAI
AZURE_OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
deployment = "gpt-5-chat"
api_version = "2024-12-01-preview"

# ----- AZURE CLIENT SETUP -----
# Blob Storage client
blob_service_client = BlobServiceClient.from_connection_string(
    STORAGE_CONNECTION_STRING
)
container_client = blob_service_client.get_container_client(STORAGE_CONTAINER)

# Cosmos DB client 
cosmos_client = CosmosClient(COSMOS_ENDPOINT, credential=COSMOS_KEY)
db = cosmos_client.get_database_client(COSMOS_DATABASE)
cosmos_container = db.get_container_client(COSMOS_CONTAINER)

# Azure OpenAI
client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
)


# ----- HELPER FUNCTIONS -----
def compute_document_id(file_name: str, file_bytes: bytes) -> str:
    """
    Compute a stable (deterministic) document ID based on:
      - the original filename
      - the file contents (bytes)

    Same filename + same bytes => same ID.
    Uses SHA-256 and truncates the hex digest for readability.
    """
    h = hashlib.sha256()
    h.update(file_name.encode("utf-8"))
    h.update(file_bytes)
    return f"{file_name}-{h.hexdigest()[:16]}"

def pdf_bytes_to_text(pdf_bytes: bytes) -> str:
    """
    Convert raw PDF bytes into extracted text by:
      - reading the PDF in-memory
      - extracting text from each page
      - concatenating pages with a page delimiter header

    Returns a single string containing the document text.
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    chunks = []
    for idx, page in enumerate(reader.pages, start=1):
        txt = (page.extract_text() or "").strip()
        if txt:
            chunks.append(f"\n\n--- PAGE {idx} ---\n{txt}")
    return "".join(chunks).strip()

def extract_fields_with_aoai(client: AzureOpenAI, document_text: str) -> str:
    """
    Call Azure OpenAI to extract structured fields from Dutch construction spec docs ("lastenboeken").

    Expected output: JSON string that matches the schema:
      {
        "architect": string|null,
        "client": string|null,
        "date": string|null,        # ISO YYYY-MM-DD if possible
        "address": string|null,
        "extractionConfidence": number
      }

    Returns:
      - A JSON string (not yet parsed) containing the extracted fields.
    """

    # Prepare prompts
    system_prompt = (
        "You are an information extraction assistant for Dutch construction specification documents "
        '("lastenboeken"). Return ONLY valid JSON. No markdown, no explanation.'
    )

    user_prompt = (
        "Extract the following fields from the document text:\n"
        "- architect: the architect of the project\n"
        "- client: the opdrachtgever / bouwheer\n"
        "- date: the document/project date in ISO format YYYY-MM-DD if possible, else null\n"
        "- address: the project address\n\n"
        "Return exactly this JSON structure:\n"
        "{\n"
        '  "architect": string|null,\n'
        '  "client": string|null,\n'
        '  "date": string|null,\n'
        '  "address": string|null,\n'
        '  "extractionConfidence": number\n'
        "}\n\n"
        "Document text:\n"
        f"{document_text}"
    )

    # Call Azure OpenAI
    response = client.chat.completions.create(
        model=deployment, 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=600,
        response_format={"type": "json_object"},
    )

    # Extract content
    content = (response.choices[0].message.content or "").strip()
    return content

def main():
    """
    Main pipeline:
      1) List blobs in the configured Blob Storage container
      2) For each PDF blob:
          - download bytes
          - compute stable document ID
          - extract PDF text
          - use Azure OpenAI to extract fields as JSON
          - upsert an item into Cosmos DB
    """
    
    print(f"Reading PDFs from storage container: {STORAGE_CONTAINER}")

    # List blobs in container
    blobs = list(container_client.list_blobs())
    if not blobs:
        print("No blobs found.")
        return

    for blob in blobs:
        name = blob.name

        # Process only PDF files
        if not name.lower().endswith(".pdf"):
            continue

        print(f"\n--- Processing: {name} ---")

        # Download blob bytes
        blob_client = container_client.get_blob_client(name)
        pdf_bytes = blob_client.download_blob().readall()

        # Compute document ID
        document_id = compute_document_id(name, pdf_bytes)

        # Extract text
        text = pdf_bytes_to_text(pdf_bytes)

        # Extract fields with Azure OpenAI
        extraction = extract_fields_with_aoai(client, text)

        # Parse JSON extraction
        data = json.loads(extraction) 

        # Build Cosmos item
        item = {
            "id": document_id,         
            "documentId": document_id, 
            "fileName": name,
            "architect": data["architect"],
            "client": data["client"],
            "date": data["date"],
            "address": data["address"],
            "extractionConfidence": data["extractionConfidence"],
        }
        
        # Upsert item into Cosmos DB
        cosmos_container.upsert_item(item)
        print(f"Upserted Cosmos item: documentId={document_id}")

    print("\nDone.")

if __name__ == "__main__":
    main()