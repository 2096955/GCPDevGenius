import os
import sys
import pathlib

# Set up service account credentials path
current_dir = pathlib.Path(__file__).parent
project_root = current_dir.parent
service_account_path = project_root / "service-account.json"

# Project ID from the service account (from service-account.json)
project_id = "gbg-neuro"
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id

if service_account_path.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(service_account_path)
    print(f"Using service account from: {service_account_path}")
    print(f"Using project ID: {project_id}")
else:
    print(f"Warning: Service account file not found at {service_account_path}")

print("\n=== GCP Dependency Check Script ===\n")

results = {}

# 1. google-cloud-storage
def check_gcs():
    try:
        from google.cloud import storage
        client = storage.Client(project=project_id)
        buckets = list(client.list_buckets())
        print(f"[SUCCESS] google-cloud-storage: Found {len(buckets)} bucket(s). Example: {buckets[0].name if buckets else 'No buckets found.'}")
        return True
    except Exception as e:
        print(f"[FAIL] google-cloud-storage: {e}")
        return False

# 2. google-cloud-firestore
def check_firestore():
    try:
        from google.cloud import firestore
        db = firestore.Client(project=project_id)
        collections = list(db.collections())
        print(f"[SUCCESS] google-cloud-firestore: Found {len(collections)} collection(s). Example: {collections[0].id if collections else 'No collections found.'}")
        return True
    except Exception as e:
        print(f"[FAIL] google-cloud-firestore: {e}")
        return False

# 3. google-cloud-aiplatform
def check_aiplatform():
    try:
        from google.cloud import aiplatform
        aiplatform.init(project=project_id, location="us-central1")
        models = aiplatform.Model.list()
        print(f"[SUCCESS] google-cloud-aiplatform: Found {len(models)} model(s). Example: {models[0].display_name if models else 'No models found.'}")
        return True
    except Exception as e:
        print(f"[FAIL] google-cloud-aiplatform: {e}")
        return False

# 4. firebase-admin
def check_firebase_admin():
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore as fb_firestore
        if not firebase_admin._apps:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                'projectId': project_id,
            })
        db = fb_firestore.client()
        print(f"[SUCCESS] firebase-admin: Firestore client initialized. {db}")
        return True
    except Exception as e:
        print(f"[FAIL] firebase-admin: {e}")
        return False

results['google-cloud-storage'] = check_gcs()
results['google-cloud-firestore'] = check_firestore()
results['google-cloud-aiplatform'] = check_aiplatform()
results['firebase-admin'] = check_firebase_admin()

print("\n=== Summary ===")
for dep, ok in results.items():
    print(f"{dep}: {'OK' if ok else 'FAILED'}")

if all(results.values()):
    print("\nAll GCP dependencies are working with the provided credentials!")
else:
    print("\nSome dependencies failed. Please review the errors above and check your credentials and IAM permissions.") 