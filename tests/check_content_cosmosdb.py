# inspect_cosmos.py
import os
from dotenv import load_dotenv
from azure.cosmos import CosmosClient

load_dotenv()

endpoint = os.environ["COSMOS_ENDPOINT"]
key = os.environ["COSMOS_KEY"]
db_name = os.getenv("COSMOS_DATABASE", "LastenboekenDb")
container_name = os.getenv("COSMOS_CONTAINER", "LastenboekenDbContainer")

client = CosmosClient(endpoint, credential=key)
db = client.get_database_client(db_name)
container = db.get_container_client(container_name)

print(f"Database: {db_name}")
print(f"Container: {container_name}\n")

# List a few items
query = "SELECT TOP 20 c.id, c.documentId, c.fileName, c.architect, c.client, c.date, c.address FROM c"
items = list(container.query_items(query=query, enable_cross_partition_query=True))

for i, it in enumerate(items, 1):
    print(f"Filename: {i}. {it.get('fileName')}")
    print(f"Architect: {it.get('architect')}")
    print(f"Client: {it.get('client')}")
    print(f"Date: {it.get('date')}")
    print(f"Address: {it.get('address')}")
    print(f"id: {it.get('id')}\n")

print(f"Total shown: {len(items)}")
