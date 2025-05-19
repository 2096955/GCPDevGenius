import os
from dotenv import load_dotenv

# Load environment variables from .env file
print("1. Attempting to load .env file...")
load_dotenv()
print("2. Environment file loaded")

# Check if variables are available
print(f"3. GOOGLE_CLOUD_PROJECT: {os.getenv('GOOGLE_CLOUD_PROJECT')}")
print(f"4. GOOGLE_CLOUD_REGION: {os.getenv('GOOGLE_CLOUD_REGION')}")
print(f"5. GCP_KEY_1: {os.getenv('GCP_KEY_1')}")
print(f"6. GCP_KEY_2: {os.getenv('GCP_KEY_2')}")
print(f"7. GCP_KEY_3: {os.getenv('GCP_KEY_3')}")
print(f"8. GCP_KEY_4: {os.getenv('GCP_KEY_4')}")
print(f"9. GCP_KEY_5: {os.getenv('GCP_KEY_5')}")
print(f"10. GCP_KEY_6: {os.getenv('GCP_KEY_6')}")

print("\nTest complete. If variables show 'None', they are not being loaded correctly.") 