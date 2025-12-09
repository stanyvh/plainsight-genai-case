import os
from azure.cosmos import CosmosClient
from dotenv import load_dotenv

load_dotenv()

endpoint = os.environ["COSMOS_ENDPOINT"]
key = os.environ["COSMOS_KEY"]
db_name = "LastenboekenDb"

print("Connecting to Cosmos...")
client = CosmosClient(endpoint, credential=key)

db = client.get_database_client(db_name)

print("Listing containers:")
for container in db.list_containers():
    print(" -", container["id"])

print("Success! Cosmos DB connection works.")

