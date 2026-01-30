from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
import json

load_dotenv()

api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
cx = os.getenv("GOOGLE_SEARCH_CX")

print(f"Using Key: {api_key[:5]}...{api_key[-5:]}")
print(f"Using CX: {cx}")

try:
    service = build("customsearch", "v1", developerKey=api_key)
    print("Service built. Executing query...")
    res = service.cse().list(q='Harvard University', cx=cx, num=1).execute()
    print("Success!")
    print(json.dumps(res, indent=2))
except Exception as e:
    print("\n--- ERROR DETECTED ---")
    print(e)
    if hasattr(e, 'content'):
        print("\n--- FULL ERROR CONTENT ---")
        print(e.content.decode('utf-8'))
