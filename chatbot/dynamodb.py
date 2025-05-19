from google.cloud import firestore
import uuid
import datetime
from utils import retrieve_environment_variables

class FirestorePersistence():
    def __init__(self, firestore_client=None):
        # Accept a Firestore client or create a new one
        if firestore_client is None:
            self.firestore_client = firestore.Client()
        else:
            self.firestore_client = firestore_client
        self.CONVERSATION_COLLECTION = retrieve_environment_variables("CONVERSATION_COLLECTION_NAME") or "conversations"
        self.FEEDBACK_COLLECTION = retrieve_environment_variables("FEEDBACK_COLLECTION_NAME") or "feedback"
        self.SESSION_COLLECTION = retrieve_environment_variables("SESSION_COLLECTION_NAME") or "sessions"

    # Store conversation details in Firestore
    def save_session(self, conversation_id, name, email):
        doc_ref = self.firestore_client.collection(self.SESSION_COLLECTION).document(conversation_id)
        doc_ref.set({
            'conversation_id': conversation_id,
            'user_name': name,
            'user_email': email,
            'session_start_time': datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        })

    # Store conversation details in Firestore
    def save_conversation(self, conversation_id, prompt, response):
        doc_ref = self.firestore_client.collection(self.CONVERSATION_COLLECTION).document()
        doc_ref.set({
            'conversation_id': conversation_id,
            'uuid': str(uuid.uuid4()),
            'user_response': prompt,
            'assistant_response': response,
            'conversation_time': datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        })

    # Update session with a presigned URL (or similar attribute)
    def update_session(self, conversation_id, presigned_url):
        doc_ref = self.firestore_client.collection(self.SESSION_COLLECTION).document(conversation_id)
        doc_ref.update({
            'presigned_url': presigned_url,
            'session_update_time': datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        })
        return doc_ref.get().to_dict()
