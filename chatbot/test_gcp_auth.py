import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
print("1. Loading environment variables...")
load_dotenv()
print("2. Environment variables loaded")

# Get GCP variables
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
region = os.getenv('GOOGLE_CLOUD_REGION')
api_key = os.getenv('GCP_KEY_1')  # Using the first API key for testing

print(f"3. Project ID: {project_id}")
print(f"4. Region: {region}")
print(f"5. API Key available: {'Yes' if api_key else 'No'}")

if not api_key:
    print("ERROR: No API key found. Please check your .env file.")
    exit(1)

# Test a simple Cloud Storage API call to list buckets
# This only tests API key authentication, not full service account credentials
try:
    print("\n6. Testing GCP API key with a simple request...")
    # Just format a simple URL that would require authentication
    # We're not actually executing this request since it requires proper setup
    url = f"https://storage.googleapis.com/storage/v1/b?project={project_id}&key={api_key}"
    
    print(f"7. Would try to access: https://storage.googleapis.com/storage/v1/b?project={project_id}&key=[API_KEY_HIDDEN]")
    print("8. Not executing actual request to protect API key and avoid unintended GCP charges")
    
    # In a real test, you would do something like:
    # response = requests.get(url)
    # print(f"Response status code: {response.status_code}")
    # print(f"Response body: {response.json()}")
    
    print("\nTest complete! Environment variables are loaded correctly.")
    print("To fully test GCP authentication, you would need to:")
    print("1. Install the required GCP client libraries")
    print("2. Set up proper authentication credentials (service account key)")
    print("3. Run a full application test")
except Exception as e:
    print(f"Error testing GCP API: {e}") 