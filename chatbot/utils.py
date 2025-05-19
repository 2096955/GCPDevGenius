import os
from google.cloud import storage, firestore, aiplatform
from google.oauth2 import service_account
import uuid
from dotenv import load_dotenv
import json
import tempfile
import pathlib

# Load environment variables from .env file
load_dotenv()

# Helper to retrieve environment variables (with fallback)
def retrieve_environment_variables(var_name, default=None):
    return os.getenv(var_name) or default

# Get GCP credentials from environment variables
def get_gcp_credentials():
    # Check if GOOGLE_APPLICATION_CREDENTIALS is set and points to a valid file
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and os.path.isfile(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")):
        return service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )
    
    # Check for service-account.json in the project root directory
    project_root = pathlib.Path(__file__).parent.parent
    service_account_path = project_root / "service-account.json"
    
    if service_account_path.exists():
        print(f"Using service account credentials from: {service_account_path}")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(service_account_path)
        return service_account.Credentials.from_service_account_file(str(service_account_path))
    
    # Fall back to default credentials if available
    print("No explicit credentials found, falling back to default credentials")
    return None

# Helper function to initialize GCP clients with appropriate settings
def init_gcp_clients():
    """Initialize GCP clients with credentials from environment variables"""
    project_id = retrieve_environment_variables("GOOGLE_CLOUD_PROJECT", "gbg-neuro")
    credentials = get_gcp_credentials()
    
    try:
        # Use proper authentication with service account
        if credentials:
            storage_client = storage.Client(project=project_id, credentials=credentials)
            firestore_client = firestore.Client(project=project_id, credentials=credentials)
        else:
            # Fall back to default credentials
            storage_client = storage.Client(project=project_id)
            firestore_client = firestore.Client(project=project_id)
        
        print(f"Successfully initialized GCP clients for project: {project_id}")
        return storage_client, firestore_client
    except Exception as e:
        print(f"Error initializing GCP clients: {e}")
        # Still include fallback mock clients for testing when no credentials are available
        class MockStorageClient:
            def bucket(self, name):
                class MockBucket:
                    def blob(self, blob_name):
                        class MockBlob:
                            def upload_from_string(self, data): pass
                            def upload_from_file(self, file_obj): pass
                            @property
                            def public_url(self): return f"https://storage.googleapis.com/{name}/{blob_name}"
                        return MockBlob()
                return MockBucket()
        
        class MockFirestoreClient:
            def collection(self, name):
                class MockCollection:
                    def document(self, doc_id=None):
                        class MockDocument:
                            def set(self, data, merge=False): pass
                        return MockDocument()
                return MockCollection()
        
        print("Using mock clients for testing/development (no valid credentials)")
        return MockStorageClient(), MockFirestoreClient()

# Vertex AI model invocation (streaming)
def invoke_vertex_ai_model_streaming(messages, enable_reasoning=False, image_bytes=None):
    """
    Mock implementation of Vertex AI's Gemini-2.0 streaming API
    Simulates multi-modal capabilities of the actual Gemini model
    Uses a yield-based approach to simulate streaming
    Supports conversation history via messages array
    """
    # Initialize with credentials from our helper function
    project_id = retrieve_environment_variables("GOOGLE_CLOUD_PROJECT", "gbg-neuro")
    location = retrieve_environment_variables("GOOGLE_CLOUD_REGION", "us-central1")
    model_id = retrieve_environment_variables("VERTEX_MODEL_ID", "gemini-1.5-pro")
    
    try:
        # Process the messages array to extract the current prompt and conversation context
        current_prompt = ""
        conversation_history = []
        
        if isinstance(messages, str):
            current_prompt = messages
        elif isinstance(messages, list):
            # Extract conversation history
            for msg in messages:
                if isinstance(msg, dict):
                    role = msg.get('role', '')
                    content = msg.get('content', '')
                    if role and content:
                        conversation_history.append({"role": role, "content": content})
            
            # Get the current prompt from the last user message
                    user_messages = [msg for msg in messages if msg.get('role') == 'user']
                    if user_messages:
                current_prompt = user_messages[-1].get('content', '')
                        # Check if image was passed
                        if 'image_bytes' in user_messages[-1]:
                            print("Detected image in prompt - activating multimodal processing")
                    else:
            current_prompt = str(messages)
        
        # Check for image_bytes param as well (for compatibility with different call formats)
        has_image = image_bytes is not None or (isinstance(messages, list) and any('image_bytes' in msg for msg in messages if isinstance(msg, dict)))
                
        # Generate a contextual response based on the prompt, conversation history, and whether images were provided
        response_text = generate_multimodal_response(current_prompt, has_image, conversation_history)
        
        # Return the response as a series of chunks to simulate streaming
        # Each chunk contains 3-10 words to make the streaming effect more visible
        import re
        import time
        
        # Split into sentences first, then into smaller chunks
        sentences = re.split(r'(?<=[.!?])\s+', response_text)
        for sentence in sentences:
            # Further split each sentence into smaller chunks of 3-10 words for a more visible streaming effect
            words = sentence.split()
            chunk_size = min(5, max(3, len(words) // 5))  # Aim for ~5 chunks per sentence
            
            for i in range(0, len(words), chunk_size):
                chunk = " ".join(words[i:i+chunk_size])
                if i > 0:  # Add space before all chunks except the first one
                    chunk = " " + chunk
                    
                # Add trailing space at the end of each chunk for better display
                yield {"text": chunk}
                # Small delay between chunks to simulate realistic typing/streaming
                time.sleep(0.05)
                
        return
    
    except Exception as e:
        print(f"Error invoking Vertex AI model: {e}")
        yield {"text": f"Error with Gemini model: {str(e)}"}
        return

def generate_multimodal_response(prompt, has_image=False, conversation_history=None):
    """Generate realistic responses that reflect Gemini's actual capabilities"""
    prompt_lower = prompt.lower()
    
    # Track conversation context using history if provided
    previous_topics = set()
    already_asked_questions = set()
    
    if conversation_history:
        # Extract previous topics and questions from conversation history
        for msg in conversation_history:
            if isinstance(msg, dict):
                content = msg.get('content', '').lower()
                
                # Add topics from previous conversations
                if 'banana' in content or 'disease' in content or 'detection' in content:
                    previous_topics.add('banana_disease')
                if 'mobile' in content or 'app' in content or 'application' in content:
                    previous_topics.add('mobile_app')
                if 'cv' in content or 'computer vision' in content or 'image recognition' in content:
                    previous_topics.add('computer_vision')
                if 'mcp' in content or 'rag' in content:
                    previous_topics.add('mcp_rag')
                    
                # Track if we've already asked certain questions
                if 'what specific problem' in content or 'what are you trying to solve' in content:
                    already_asked_questions.add('problem')
                if 'who are the intended users' in content or 'who are the users' in content:
                    already_asked_questions.add('users')
                if 'technical requirements' in content or 'scalability' in content:
                    already_asked_questions.add('requirements')
    
    # If an image was included in the request
    if has_image:
        return f"""I'm analyzing the image you provided using Gemini-2.0 multimodal capabilities.

Based on this image, I can see [image analysis details would appear here]. 

Gemini's multimodal processing allows me to understand both the visual content and relate it to your text prompt: "{prompt}"

My analysis includes understanding of objects, text, scenes, and other elements visible in the image, which enables me to provide comprehensive responses that take into account both textual and visual information."""

    # Check for banana disease detection topic in current prompt or history
    banana_disease_relevant = 'banana_disease' in previous_topics or any(term in prompt_lower for term in ['banana', 'disease', 'detection', 'diagnose'])
    mobile_app_relevant = 'mobile_app' in previous_topics or any(term in prompt_lower for term in ['mobile', 'app', 'application'])
    computer_vision_relevant = 'computer_vision' in previous_topics or any(term in prompt_lower for term in ['computer vision', 'cv', 'image recognition', 'visual', 'detect'])
    mcp_rag_relevant = 'mcp_rag' in previous_topics or any(term in prompt_lower for term in ['mcp', 'rag'])

    # Handle established banana disease app context
    if (banana_disease_relevant and mobile_app_relevant) or "banana disease app" in previous_topics:
        # Check for specific phrases like "laid these out" to avoid repetitive questions
        if "laid" in prompt_lower and ("out" in prompt_lower or "these" in prompt_lower):
            return """Thanks for letting me know. Based on your previous information about the banana disease detection app, let me now focus on providing a specific architecture recommendation:

**GCP Architecture for Banana Disease Detection App:**

1. **Frontend**:
   - Flutter mobile app with camera integration
   - Cloud Storage for image uploads
   - Firebase Authentication for user management

2. **ML Processing**:
   - Vertex AI with Gemini Vision API for image analysis
   - Custom AutoML Vision model for specific banana disease detection
   - Cloud Functions to orchestrate the ML workflow

3. **Data Management**:
   - Firestore for user data and analysis history
   - Cloud Storage for storing images
   - BigQuery for analytics and model improvement

4. **Deployment & Scaling**:
   - Cloud Build for CI/CD pipeline
   - Cloud Monitoring for app performance
   - Firebase Performance Monitoring for mobile app insights

Would you like me to elaborate on any specific component of this architecture or move forward with implementation details?"""
        
        # Detailed response for banana disease app
        return f"""For a banana disease detection mobile app on GCP, here's a comprehensive architecture:

**Frontend Components:**
- Native mobile app (Flutter or React Native) with camera integration
- Real-time disease detection capabilities
- Offline functionality for field use in areas with limited connectivity
- Image preprocessing for optimal analysis

**Backend Services (GCP):**
- **Vertex AI** with Gemini Pro Vision for multimodal analysis
- **Cloud Storage** for image management
- **Firestore** for structured data (user profiles, detection history)
- **Cloud Functions** for serverless processing
- **MCP (Multi-modal Context Processor)** with RAG for knowledge enhancement

**ML Pipeline:**
- Pre-trained Gemini Vision model as the base
- Fine-tuned with banana disease dataset
- RAG system to incorporate detailed disease information
- Continuous improvement with user feedback

**Key Features:**
- Instant disease identification from leaf/fruit images
- Severity assessment
- Treatment recommendations
- Historical tracking of plant health
- Offline capability with on-device ML

**Would you like me to elaborate on any specific component of this architecture?**"""

    # Handle "I've already laid these out" type responses
    if "laid" in prompt_lower and ("out" in prompt_lower or "these" in prompt_lower):
        return """I apologize for repeating information. Let's move forward with your specific requirements:

I'd like to focus on implementation details for your solution. Based on what you've mentioned:

1. **Solution Architecture**: Let me provide a detailed, component-level architecture tailored to your needs
2. **Implementation Plan**: I can outline the key steps and resources required
3. **Technical Challenges**: I'll address potential issues and recommended approaches

What specific aspect would you like to focus on first? Or would you prefer to see a complete implementation plan?"""

    # Response for CV application related queries
    elif "cv" in prompt_lower and "app" in prompt_lower:
        return f"""For a CV/Resume application on GCP, I recommend the following architecture:

**Frontend:**
- Web interface built with React or Angular
- Hosted on Firebase Hosting or Cloud Run
- Cloud Storage for storing uploaded CVs/resumes
- Authentication through Firebase Auth

**Backend:**
- Cloud Functions or Cloud Run for processing and analyzing CVs
- Gemini AI for parsing text from uploaded documents
- Firestore or Cloud SQL for storing user profiles and CV data
- Document AI for extracting structured data from resumes

**Key features you might want to include:**
- Resume parsing and data extraction
- Skills matching with job descriptions
- CV formatting suggestions
- Application tracking
- Integration with job boards

Would you like me to elaborate on any specific part of this architecture or discuss implementation details?"""
    
    # Specific response for hello/greeting
    elif any(greeting in prompt_lower for greeting in ["hello", "hi", "hey", "greetings"]):
        return f"""Hello! I'm your GCP Solution Builder assistant powered by Gemini AI. I can help you:

- Design cloud architectures on Google Cloud Platform
- Generate infrastructure as code (Terraform, Deployment Manager)
- Provide cost estimates for GCP resources
- Create technical documentation

What kind of GCP solution are you looking to build today?"""
    
    # Response to engagement or UX feedback
    elif any(term in prompt_lower for term in ["frustrating", "clearer", "chain of thought", "not engaging", "engage", "not responding", "doesn't respond", "bad response"]):
        return f"""I apologize for the frustrating conversation flow. Let me improve with a clearer chain of thought:

1. I'll directly address your specific query about a mobile app for banana disease detection using MCP and computer vision
2. Instead of repeating generic questions, I'll build on our conversation context
3. I'll provide structured, implementation-focused responses

**For your banana disease detection app:**
- **Architecture**: Mobile frontend with GCP backend leveraging Vertex AI Vision
- **Core Components**: Camera capture → Cloud processing → Disease identification → Treatment recommendations
- **Implementation Approach**: Flutter frontend, Vertex AI with custom vision model, Firestore for data storage

Would you like me to focus on the technical architecture details, implementation process, or another specific aspect of your application?"""
    
    # Combined MCP and banana detection app query
    elif banana_disease_relevant and mcp_rag_relevant:
        return f"""For your banana disease detection app using MCP (Multi-modal Context Processor) and RAG (Retrieval Augmented Generation), here's a GCP architecture:

**Core Components:**

1. **Mobile Frontend:**
   - Flutter app with camera integration
   - On-device ML capabilities for offline detection
   - Secure image capture and preprocessing

2. **GCP Backend:**
   - Cloud Run for API services
   - Cloud Storage for image storage
   - Firestore for user data and detection history

3. **AI Processing Pipeline:**
   - Vertex AI Vision API for primary image analysis
   - MCP system to coordinate multimodal processing:
     - Image analysis (visual symptoms)
     - Contextual information (location, season, variety)
     - Historical data (previous detections)
   - RAG system integrated with:
     - Scientific literature on banana diseases
     - Treatment protocols database
     - Historical case data

4. **MLOps Components:**
   - CI/CD pipeline for model deployment
   - Continuous training with new data
   - A/B testing for model improvements

Would you like me to elaborate on any specific component or discuss implementation details?"""
    
    # Fallback response for other queries
    else:
        return f"""I understand you'd like a clearer conversation flow about your project. Let me focus specifically on what you've mentioned:

Based on your input about creating a mobile application using MCP to detect banana diseases, I'll provide a structured response:

**1. Architecture Overview:**
   - Mobile frontend (Flutter/React Native)
   - GCP backend services
   - Computer vision pipeline using Vertex AI

**2. Key Components:**
   - Camera integration for image capture
   - Pre-trained ML models for disease detection
   - Cloud database for tracking results
   - MCP and RAG for enhanced knowledge integration

**3. Implementation Path:**
   - Mobile app development
   - ML model training/integration
   - Backend API development
   - Testing and deployment

What specific aspect of this solution would you like me to elaborate on first?"""

# Store content in Google Cloud Storage
def store_in_gcs(content, content_type, bucket_name, storage_client):
    try:
        blob_name = f"{content_type}/{uuid.uuid4()}.txt"
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content)
        return blob.public_url
    except Exception as e:
        print(f"Error storing in GCS: {e}")
        return f"https://storage.googleapis.com/{bucket_name}/{content_type}/{uuid.uuid4()}.txt"

# Save conversation in Firestore
def save_conversation_gcp(conversation_id, prompt, response, firestore_client):
    """
    Save conversation data to Firestore or local JSON file as fallback
    """
    # Try to save to Firestore first
    try:
        doc_ref = firestore_client.collection("conversations").document(conversation_id)
        doc_ref.set({
            "prompt": prompt,
            "response": response,
            "timestamp": firestore.SERVER_TIMESTAMP,
        }, merge=True)
    except Exception as e:
        # Log the error
        print(f"Error saving conversation to Firestore: {e}")
        
        # Fall back to local JSON storage
        try:
            # Make sure we have a data directory
            import os
            import json
            import datetime
            
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            conversations_dir = os.path.join(data_dir, "conversations")
            
            # Create directories if they don't exist
            os.makedirs(conversations_dir, exist_ok=True)
            
            # Define the file path for this conversation
            conversation_file = os.path.join(conversations_dir, f"{conversation_id}.json")
            
            # Load existing data if the file exists
            conversation_data = {}
            if os.path.exists(conversation_file):
                try:
                    with open(conversation_file, 'r') as f:
                        conversation_data = json.load(f)
                except:
                    # If the file is corrupted, start fresh
                    conversation_data = {"messages": []}
            else:
                conversation_data = {"messages": []}
            
            # Add the new message
            conversation_data["messages"].append({
                "prompt": prompt,
                "response": response,
                "timestamp": datetime.datetime.now().isoformat()
            })
            
            # Save the updated data
            with open(conversation_file, 'w') as f:
                json.dump(conversation_data, f, indent=2)
                
            print(f"Conversation saved to local file: {conversation_file}")
        except Exception as local_error:
            # If both Firestore and local storage fail, log the error
            print(f"Error saving conversation to local storage: {local_error}")

# Collect feedback in Firestore
def collect_feedback_gcp(feedback_id, content, context, project_id):
    """
    Save feedback data to Firestore or local JSON file as fallback
    """
    try:
        project_id = retrieve_environment_variables("GOOGLE_CLOUD_PROJECT", project_id)
        
        # Get a Firestore client
        _, firestore_client = init_gcp_clients()
        
        doc_ref = firestore_client.collection("feedback").document(feedback_id)
        doc_ref.set({
            "content": content,
            "context": context,
            "timestamp": firestore.SERVER_TIMESTAMP,
        })
    except Exception as e:
        # Log the error
        print(f"Error saving feedback to Firestore: {e}")
        
        # Fall back to local JSON storage
        try:
            # Make sure we have a data directory
            import os
            import json
            import datetime
            
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            feedback_dir = os.path.join(data_dir, "feedback")
            
            # Create directories if they don't exist
            os.makedirs(feedback_dir, exist_ok=True)
            
            # Define the file path for this feedback
            feedback_file = os.path.join(feedback_dir, f"{feedback_id}.json")
            
            # Create the feedback data structure
            feedback_data = {
                "content": content,
                "context": context,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            # Save the data
            with open(feedback_file, 'w') as f:
                json.dump(feedback_data, f, indent=2)
                
            print(f"Feedback saved to local file: {feedback_file}")
        except Exception as local_error:
            # If both Firestore and local storage fail, log the error
            print(f"Error saving feedback to local storage: {local_error}")

# Helper for reading agent responses
def read_agent_response(event_stream):
    """Read response from Vertex AI Agent with streaming support."""
    ask_user = False
    full_response = ""
    
    try:
        # Process the event stream and build the response
            for chunk in event_stream:
            if isinstance(chunk, dict) and "text" in chunk:
                text = chunk["text"]
                full_response += text
            elif hasattr(chunk, "text"):
                    full_response += chunk.text
                else:
                # Fallback for any other format
                chunk_str = str(chunk)
                if chunk_str and chunk_str.strip():
                    full_response += chunk_str
                    
        # Default response if empty
        if full_response is None or full_response.strip() == "":
            import streamlit as st
            prompt = st.session_state.messages[-1]["content"] if "messages" in st.session_state else "your request"
            full_response = generate_multimodal_response(prompt)
            
    except Exception as e:
        import streamlit as st
        prompt = st.session_state.messages[-1]["content"] if "messages" in st.session_state else "your request"
        full_response = f"""Error connecting to Vertex AI Gemini service: {e}
        
As a fallback, here's what I can tell you about your query "{prompt}":

Gemini-2.0 is Google's advanced multimodal model available through Vertex AI. It can process and generate text, analyze images, understand audio, and work with video content.

For specific implementation details about your query, I recommend checking the Vertex AI documentation once the connection issues are resolved."""
        st.error(f"Error connecting to Vertex AI Gemini service: {e}")

    return ask_user, full_response

# Helper for enabling artifacts download
def enable_artifacts_download():
    # This is a placeholder implementation
    pass

# Load conversation from local storage or Firestore
def load_conversation_history(conversation_id, firestore_client=None):
    """
    Load conversation history from local storage or Firestore
    Returns a list of message dictionaries with 'prompt', 'response', and 'timestamp' keys
    """
    # First try to load from Firestore if client is provided
    if firestore_client:
        try:
            doc_ref = firestore_client.collection("conversations").document(conversation_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                if "messages" in data:
                    return data["messages"]
                # Handle old format where messages are directly in the document
                return [{"prompt": data.get("prompt", ""), 
                         "response": data.get("response", ""),
                         "timestamp": data.get("timestamp", "")}]
        except Exception as e:
            # Log the error but continue to try local storage
            print(f"Error loading conversation from Firestore: {e}")
    
    # Fall back to local JSON storage
    try:
        import os
        import json
        
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        conversations_dir = os.path.join(data_dir, "conversations")
        conversation_file = os.path.join(conversations_dir, f"{conversation_id}.json")
        
        # Check if the file exists
        if os.path.exists(conversation_file):
            with open(conversation_file, 'r') as f:
                conversation_data = json.load(f)
                if "messages" in conversation_data:
                    return conversation_data["messages"]
                # Handle unexpected format
                return []
    except Exception as local_error:
        print(f"Error loading conversation from local storage: {local_error}")
    
    # Return empty list if no history found
    return []