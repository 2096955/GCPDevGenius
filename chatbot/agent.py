import streamlit as st
import os
from google.cloud import aiplatform, storage, firestore
from google.oauth2 import service_account
from PIL import Image
from utils import (
    invoke_vertex_ai_model_streaming,
    read_agent_response,
    enable_artifacts_download,
    retrieve_environment_variables,
    save_conversation_gcp,
    init_gcp_clients,
)
from layout import create_tabs, create_option_tabs, welcome_sidebar, login_page
from styles import apply_styles
from cost_estimate_widget import generate_cost_estimates
from generate_arch_widget import generate_arch
from generate_terraform_widget import generate_terraform
from generate_dm_widget import generate_deployment_manager
from generate_doc_widget import generate_doc
import io

# Import A2A client components - wrap in try-except to handle missing dependencies
try:
    from a2a.common import A2AClient, Message, TextPart
    import asyncio
    import uuid
    A2A_AVAILABLE = True
except ImportError:
    print("A2A dependencies not available. Will use Vertex AI only.")
    A2A_AVAILABLE = False
    # Define dummy asyncio for non-A2A operation
    import asyncio
    import uuid

# Streamlit configuration 
st.set_page_config(page_title="DevGenius (GCP)", layout='wide')
apply_styles()

# GCP Project and Region
GCP_PROJECT = retrieve_environment_variables("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
GCP_REGION = retrieve_environment_variables("GOOGLE_CLOUD_REGION", "us-central1")

# Initialize GCP clients
storage_client, firestore_client = init_gcp_clients()

# A2A Host Agent configuration (default to localhost)
HOST_AGENT_URL = retrieve_environment_variables("HOST_AGENT_URL", "http://localhost:8000")
CODE_AGENT_URL = retrieve_environment_variables("CODE_AGENT_URL", "http://localhost:8001")
DATA_AGENT_URL = retrieve_environment_variables("DATA_AGENT_URL", "http://localhost:8002")

# Function to create A2A client
def get_a2a_client(agent_url=HOST_AGENT_URL):
    """Get an A2A client connected to the specified agent."""
    if not A2A_AVAILABLE:
        return None
    api_key = os.environ.get("GOOGLE_API_KEY")
    return A2AClient(agent_url=agent_url, api_key=api_key)

# Function to process request through A2A
async def process_with_a2a(prompt, agent_url=HOST_AGENT_URL):
    """Process a request through A2A and return the response."""
    if not A2A_AVAILABLE:
        return "A2A functionality is not available. Using Vertex AI instead."
    
    try:
        # Create A2A client
        client = get_a2a_client(agent_url)
        
        # Create session ID if not already present
        if 'a2a_session_id' not in st.session_state:
            st.session_state.a2a_session_id = str(uuid.uuid4())
        
        # Create message
        message = Message(
            role="user",
            parts=[TextPart(text=prompt)]
        )
        
        # Send task to agent
        task = await client.send_task(
            message=message,
            session_id=st.session_state.a2a_session_id
        )
        
        # Poll until task is done
        while task.status.state not in ["completed", "failed", "canceled"]:
            await asyncio.sleep(0.5)
            task = await client.get_task(task.id)
        
        # Extract response
        response_text = ""
        if task.status.state == "completed":
            if task.status.message:
                for part in task.status.message.parts:
                    if hasattr(part, "text"):
                        response_text += part.text
            
            if task.artifacts:
                for artifact in task.artifacts:
                    for part in artifact.parts:
                        if hasattr(part, "text"):
                            if response_text:
                                response_text += "\n\n"
                            response_text += part.text
        else:
            response_text = f"Task {task.status.state}: {task.status.message if task.status.message else 'Unknown error'}"
        
        # Close client
        await client.close()
        
        return response_text
    except Exception as e:
        return f"Error processing request with A2A: {str(e)}"

# Function to determine if a prompt should be routed to A2A
def should_route_to_a2a(prompt):
    """Determine if a prompt should be routed to A2A based on content."""
    # If A2A is not available, always return False
    if not A2A_AVAILABLE:
        return False
        
    prompt_lower = prompt.lower()
    
    # Keywords that indicate AWS to GCP migration tasks
    aws_keywords = ["aws", "amazon", "ec2", "s3", "lambda", "dynamodb", "migrate", "migration", "convert"]
    gcp_keywords = ["gcp", "google cloud", "gcs", "cloud function", "firestore", "spanner"]
    code_keywords = ["code", "convert", "translation", "transform", "refactor"]
    data_keywords = ["data", "schema", "database", "table", "storage", "bucket"]
    
    # Check if the prompt contains AWS and GCP keywords
    has_aws = any(keyword in prompt_lower for keyword in aws_keywords)
    has_gcp = any(keyword in prompt_lower for keyword in gcp_keywords)
    has_code = any(keyword in prompt_lower for keyword in code_keywords)
    has_data = any(keyword in prompt_lower for keyword in data_keywords)
    
    # Route to A2A if it mentions AWS and GCP, plus either code or data
    return (has_aws and has_gcp) and (has_code or has_data)

# Function to determine which specific agent to route to
def get_agent_for_prompt(prompt):
    """Determine which specialized agent to route to based on the prompt."""
    prompt_lower = prompt.lower()
    
    # Keywords for code conversion
    code_keywords = ["code", "convert", "function", "lambda", "ec2", "terraform", "cloudformation", "translate", "implementation"]
    
    # Keywords for data migration
    data_keywords = ["data", "schema", "database", "dynamodb", "s3", "migration", "storage", "firestore", "spanner", "bigquery"]
    
    # Count matches for each category
    code_matches = sum(1 for keyword in code_keywords if keyword in prompt_lower)
    data_matches = sum(1 for keyword in data_keywords if keyword in prompt_lower)
    
    # Route based on which category has more matches
    if code_matches > data_matches:
        return CODE_AGENT_URL
    elif data_matches > code_matches:
        return DATA_AGENT_URL
    else:
        # Default to host agent if unclear
        return HOST_AGENT_URL

def display_image(image, width=600, caption="Uploaded Image", use_center=True):
    if use_center:
        col1, col2, col3 = st.columns([1, 2, 1])
        display_container = col2
    else:
        display_container = st
    with display_container:
        st.image(
            image,
            caption=caption,
            width=width,
            use_column_width=False,
            clamp=True
        )

def get_image_insights_vertex(image_data, query="Explain in detail the architecture flow"):
    # Example Vertex AI model invocation (pseudo-code, replace with your model details)
    # You may need to adapt this to your Vertex AI model's API
    try:
        response = invoke_vertex_ai_model_streaming(
            messages=[{"role": "user", "content": query, "image_bytes": image_data}],
            enable_reasoning=True
        )
        
        # Create a styled placeholder for streaming output
        output_placeholder = st.empty()
        full_response = ""
        
        # Process streaming chunks
        for chunk in response:
            if chunk and "text" in chunk:
                text = chunk.get("text", "")
                full_response += text
                # Update the placeholder with the current content inside a styled div
                output_placeholder.markdown(
                    f"""<div style="background-color: white; color: black; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0;">
                    {full_response}
                    </div>""", 
                    unsafe_allow_html=True
                )
        
        # Clear the placeholder since we'll show the message in the chat history
        output_placeholder.empty()
        
        # Add to message history
        if 'mod_messages' not in st.session_state:
            st.session_state.mod_messages = []
        st.session_state.mod_messages.append({"role": "assistant", "content": full_response})
        st.session_state.interaction.append({"type": "Architecture details", "details": full_response})
        save_conversation_gcp(st.session_state['conversation_id'], query, full_response, firestore_client)
        
        return full_response
    except Exception as e:
        st.error(f"ERROR: Can't invoke Vertex AI model. Reason: {e}")
        return f"Error analyzing image: {e}"

def reset_chat():
    keys_to_keep = {'conversation_id', 'user_authenticated', 'user_name', 'user_email', 'firebase_authentication', 'token', 'midway_user'}
    keys_to_remove = set(st.session_state.keys()) - keys_to_keep
    for key in keys_to_remove:
        del st.session_state[key]
    st.session_state.messages = []

def reset_messages():
    initial_question = get_initial_question(st.session_state.topic_selector)
    st.session_state.messages = [{"role": "assistant", "content": "Welcome to DevGenius (GCP) — turning ideas into reality. Together, we'll design your architecture and solution, with each conversation shaping your vision. Let's get started on building!"}]
    if initial_question:
        st.session_state.messages.append({"role": "user", "content": initial_question})
        response = invoke_vertex_ai_model_streaming(
            [{"role": "user", "content": initial_question}]
        )
        event_stream = response
        ask_user, agent_answer = read_agent_response(event_stream)
        st.session_state.messages.append({"role": "assistant", "content": agent_answer})

def format_for_markdown(response_text):
    return response_text.replace("\n", "\n\n")

def get_initial_question(topic):
    return {
        "Data Lake": "How can I build an enterprise data lake on GCP?",
        "Log Analytics": "How can I build a log analytics solution on GCP?"
    }.get(topic, "")

def resize_or_compress_image(uploaded_image):
    image = Image.open(uploaded_image)
    image_bytes = uploaded_image.getvalue()
    if len(image_bytes) > 5 * 1024 * 1024:
        st.write("Image size exceeds 5MB. Resizing...")
        image = image.resize((800, 600))
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format="JPEG", quality=85)
        img_byte_arr.seek(0)
        return img_byte_arr
    else:
        return uploaded_image

# Helper function to run async tasks within Streamlit
def run_async(coroutine):
    """Run an async coroutine and return the result."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()

#########################################
# Streamlit Main Execution Starts Here
#########################################
if 'user_authenticated' not in st.session_state:
    st.session_state.user_authenticated = False
if 'interaction' not in st.session_state:
    st.session_state.interaction = []

if not st.session_state.user_authenticated:
    login_page()
else:
    tabs = create_tabs()
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "Build a solution"
    with st.sidebar:
        welcome_sidebar()
    with tabs[0]:
        st.markdown("""<h1 style="background-color: white; color: #4285F4; padding: 15px; border-radius: 8px; border: 1px solid #e0e0e0; text-align: center; margin-bottom: 20px;">
        Generate Architecture Diagram and Solution (GCP)
        </h1>""", unsafe_allow_html=True)
        if "topic_selector" not in st.session_state:
            st.session_state.topic_selector = ""
            reset_messages()
        if st.session_state.active_tab != "Build a solution":
            st.session_state.active_tab = "Build a solution"
        if "messages" not in st.session_state:
            st.session_state["messages"] = [{"role": "assistant", "content": "Welcome"}]
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(f"""<div style="background-color: white; color: black; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0;">
                {message["content"]}
                </div>""", unsafe_allow_html=True)
        
        # Make the chat input more visible with custom styling
        st.markdown("""
        <style>
        [data-testid="stChatInput"] {
            background-color: white !important;
            border: 2px solid #4285F4 !important;
            border-radius: 8px !important;
            padding: 10px !important;
        }
        [data-testid="stChatInput"] > input {
            color: black !important;
            background-color: white !important;
        }
        [data-testid="stChatInput"]::placeholder {
            color: #666 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        prompt = st.chat_input("Type your message here...", key='Generate')
        if prompt:
            st.session_state.cost = False
            st.session_state.arch = False
            st.session_state.terraform = False
            with st.chat_message("user"):
                st.markdown(f"""<div style="background-color: white; color: black; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0;">
                {prompt}
                </div>""", unsafe_allow_html=True)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            with st.chat_message("assistant"):
                # Create a placeholder for streaming response
                message_placeholder = st.empty()
                streaming_content = ""
                
                with st.spinner("Thinking..."):
                    # Check if we should route to A2A
                    if should_route_to_a2a(prompt):
                        # Get the appropriate agent URL
                        agent_url = get_agent_for_prompt(prompt)
                        
                        # Process with A2A
                        agent_answer = run_async(process_with_a2a(prompt, agent_url))
                        
                        # Add a tag to indicate this was processed by A2A
                        if A2A_AVAILABLE:
                            agent_source = "Code Conversion Agent" if agent_url == CODE_AGENT_URL else "Data Migration Agent" if agent_url == DATA_AGENT_URL else "Host Agent"
                            agent_answer = f"**[Processed by {agent_source}]**\n\n{agent_answer}"
                            
                        # Display the final response in the placeholder
                        message_placeholder.markdown(f"""<div style="background-color: white; color: black; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0;">
                        {agent_answer}
                        </div>""", unsafe_allow_html=True)
                    else:
                        # Use existing Vertex AI processing with streaming
                        response = invoke_vertex_ai_model_streaming(
                            st.session_state.mod_messages + [{"role": "user", "content": prompt}]
                        )
                        
                        # Process the streaming response chunks
                        streaming_content = ""
                        for chunk in response:
                            if chunk and "text" in chunk:
                                streaming_content += chunk["text"]
                                # Update the placeholder with the current streamed content
                                message_placeholder.markdown(f"""<div style="background-color: white; color: black; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0;">
                                {streaming_content}
                                </div>""", unsafe_allow_html=True)
                        
                        # Get the final formatted response
                        ask_user, agent_answer = streaming_content, streaming_content
                    
                # Save the complete response to session state
                st.session_state.messages.append({"role": "assistant", "content": agent_answer})
                
            if not ask_user:
                st.session_state.interaction.append(
                    {"type": "Details", "details": st.session_state.messages[-1]['content']})
                enable_artifacts_download()
            save_conversation_gcp(st.session_state['conversation_id'], prompt, agent_answer, firestore_client)
    with tabs[1]:
        st.header("Generate Solution from Existing Architecture (GCP)")
        st.markdown("""
            <style>
            .stFileUploader button {
                background-color: #4285F4;
                color: white !important;
                border: none !important;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
            }
            .stFileUploader button:hover {
                background-color: #3367D6;
            }
            </style>
        """, unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Choose an image...", type=["png", "jpg", "jpeg"], on_change=reset_chat)
        if st.session_state.active_tab != "Modify your existing architecture":
            st.session_state.active_tab = "Modify your existing architecture"
        if uploaded_file:
            gcs_bucket_name = retrieve_environment_variables("GCS_BUCKET_NAME")
            bucket = storage_client.bucket(gcs_bucket_name)
            blob = bucket.blob(f"{st.session_state.conversation_id}/uploaded_file/{uploaded_file.name}")
            resized_image = resize_or_compress_image(uploaded_file)
            blob.upload_from_file(resized_image)
            st.session_state.uploaded_image = resized_image
            image = Image.open(st.session_state.uploaded_image)
            display_image(image)
            image_bytes = st.session_state.uploaded_image.getvalue()
            if 'image_insights' not in st.session_state:
                st.session_state.image_insights = get_image_insights_vertex(
                    image_data=image_bytes)
        if 'mod_messages' not in st.session_state:
            st.session_state.mod_messages = []
        if 'generate_arch_called' not in st.session_state:
            st.session_state.generate_arch_called = False
        if 'generate_cost_estimates_called' not in st.session_state:
            st.session_state.generate_cost_estimates_called = False
        if 'generate_terraform_called' not in st.session_state:
            st.session_state.generate_terraform_called = False
        for msg in st.session_state.mod_messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(f"""<div style="background-color: white; color: black; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0;">
                    {msg["content"]}
                    </div>""", unsafe_allow_html=True)
            elif msg["role"] == "assistant":
                formatted_content = format_for_markdown(msg["content"])
                with st.chat_message("assistant"):
                    st.markdown(f"""<div style="background-color: white; color: black; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0;">
                    {formatted_content}
                    </div>""", unsafe_allow_html=True)
        if uploaded_file:
            if st.session_state.interaction:
                enable_artifacts_download()

        # Add the same chat input styling here for consistency
        st.markdown("""
        <style>
        [data-testid="stChatInput"] {
            background-color: white !important;
            border: 2px solid #4285F4 !important;
            border-radius: 8px !important;
            padding: 10px !important;
        }
        [data-testid="stChatInput"] > input {
            color: black !important;
            background-color: white !important;
        }
        [data-testid="stChatInput"]::placeholder {
            color: #666 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if prompt := st.chat_input("Describe your architecture or ask a question...", key="Architecture"):
            st.session_state.generate_arch_called = False
            st.session_state.generate_terraform_called = False
            st.session_state.generate_cost_estimates_called = False
            st.session_state.mod_messages.append({"role": "user", "content": prompt})
            st.chat_message("user").markdown(prompt)
            
            with st.chat_message("assistant"):
                # Create a placeholder for streaming response
                message_placeholder = st.empty()
                streaming_content = ""
                
                with st.spinner("Thinking..."):
                    # Check if we should route to A2A (even for image descriptions)
                    if should_route_to_a2a(prompt):
                        # Get the appropriate agent URL
                        agent_url = get_agent_for_prompt(prompt)
                        
                        # Process with A2A, including image context if needed
                        if 'uploaded_image' in st.session_state:
                            # For A2A, we could add a text note about the image
                            prompt_with_context = f"{prompt}\n\n[Note: This query is related to an uploaded architecture image that shows AWS resources]"
                            response = run_async(process_with_a2a(prompt_with_context, agent_url))
                        else:
                            response = run_async(process_with_a2a(prompt, agent_url))
                        
                        # Add a tag to indicate this was processed by A2A
                        if A2A_AVAILABLE:
                            agent_source = "Code Conversion Agent" if agent_url == CODE_AGENT_URL else "Data Migration Agent" if agent_url == DATA_AGENT_URL else "Host Agent"
                            response = f"**[Processed by {agent_source}]**\n\n{response}"
                            
                        # Display the final response in the placeholder
                        message_placeholder.markdown(f"""<div style="background-color: white; color: black; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0;">
                        {response}
                        </div>""", unsafe_allow_html=True)
                        
                        # Save for interaction history
                        agent_answer = response
                    else:
                        # Use existing Vertex AI processing with streaming
                        response = invoke_vertex_ai_model_streaming(
                            st.session_state.mod_messages + [{"role": "user", "content": prompt}]
                        )
                        
                        # Process the streaming response chunks
                        streaming_content = ""
                        for chunk in response:
                            if chunk and "text" in chunk:
                                streaming_content += chunk["text"]
                                # Update the placeholder with the current streamed content
                                message_placeholder.markdown(f"""<div style="background-color: white; color: black; padding: 10px; border-radius: 5px; border: 1px solid #e0e0e0;">
                                {streaming_content}
                                </div>""", unsafe_allow_html=True)
                        
                        # Save the final content
                        agent_answer = streaming_content
                    
                    st.session_state.interaction.append({"type": "Architecture details", "details": agent_answer})
                    
            st.session_state.mod_messages.append({"role": "assistant", "content": agent_answer})
            save_conversation_gcp(st.session_state['conversation_id'], prompt, agent_answer, firestore_client)
            st.rerun()
