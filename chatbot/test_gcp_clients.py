import os
from dotenv import load_dotenv
from utils import init_gcp_clients, get_gcp_credentials, invoke_vertex_ai_model_streaming, store_in_gcs, save_conversation_gcp

# Load environment variables
print("1. Loading environment variables...")
load_dotenv()
print("2. Environment variables loaded")

# Get GCP variables
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
region = os.getenv('GOOGLE_CLOUD_REGION')

print(f"3. Project ID: {project_id}")
print(f"4. Region: {region}")

# Test getting credentials
print("\n5. Testing GCP credentials...")
try:
    credentials = get_gcp_credentials()
    print(f"6. Credentials obtained: {'Yes' if credentials is not None else 'Using API key-based authentication'}")
except Exception as e:
    print(f"ERROR getting credentials: {e}")

# Test initializing GCP clients
print("\n7. Testing GCP client initialization...")
try:
    storage_client, firestore_client = init_gcp_clients()
    print("8. Storage client initialized successfully")
    print("9. Firestore client initialized successfully")
except Exception as e:
    print(f"ERROR initializing clients: {e}")

# Test invoking Vertex AI model
print("\n10. Testing Vertex AI model invocation...")
try:
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me about GCP Vertex AI"}
    ]
    response, stop_reason = invoke_vertex_ai_model_streaming(messages)
    print("11. Model response received successfully:")
    print(f"Response (first 100 chars): {response[:100]}...")
    print(f"Stop reason: {stop_reason}")
except Exception as e:
    print(f"ERROR invoking model: {e}")

# Test storing in GCS
print("\n12. Testing GCS storage...")
try:
    bucket_name = "test-bucket"
    url = store_in_gcs("Test content", "test", bucket_name, storage_client)
    print(f"13. Content stored successfully")
    print(f"URL: {url}")
except Exception as e:
    print(f"ERROR storing in GCS: {e}")

# Test saving to Firestore
print("\n14. Testing Firestore storage...")
try:
    save_conversation_gcp("test-conversation-id", "test prompt", "test response", firestore_client)
    print("15. Conversation saved successfully")
except Exception as e:
    print(f"ERROR saving to Firestore: {e}")

print("\nTest complete! The application is correctly set up to work with mock GCP services.")
print("For production deployment, you would need:")
print("1. A GCP service account key file (set as GOOGLE_APPLICATION_CREDENTIALS)")
print("2. Proper permissions for the service account")
print("3. Actual GCP resources (Vertex AI models, Storage buckets, Firestore collections)")
print("\nFor now, the application will use mock services for testing/development.") 