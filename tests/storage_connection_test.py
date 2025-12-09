import os
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]

print("Connecting to Azure Storage...")
client = BlobServiceClient.from_connection_string(conn_str)

container_name = "plainsightgenaicase" 

container = client.get_container_client(container_name)

print(f"Listing blobs in container: {container_name}")
for blob in container.list_blobs():
    print(" -", blob.name)

print("Success! Storage connection works.")