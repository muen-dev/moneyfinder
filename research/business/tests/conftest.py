import os

# Never push test dossiers to SurrealDB (business_research.kb_sync).
os.environ["KB_AUTO_PUSH"] = "0"
