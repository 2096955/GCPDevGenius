import uuid
import streamlit as st
from utils import (
    invoke_vertex_ai_model_streaming,
    store_in_gcs,
    save_conversation_gcp,
    collect_feedback_gcp,
)
from google.cloud import storage, firestore
from google.oauth2 import service_account
import os

# GCP Project and credentials
GCP_PROJECT = os.getenv("GCP_PROJECT") or "your-gcp-project-id"
GCP_REGION = os.getenv("GCP_REGION") or "us-central1"
credentials = None
if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    )
storage_client = storage.Client(project=GCP_PROJECT, credentials=credentials)
firestore_client = firestore.Client(project=GCP_PROJECT, credentials=credentials)

# Generate documentation
@st.fragment
def generate_doc(doc_messages):

    doc_messages = doc_messages[:]

    # Retain messages and previous insights in the chat section
    if 'doc_messages' not in st.session_state:
        st.session_state.doc_messages = []

    # Create the radio button for cost estimate selection
    if 'doc_user_select' not in st.session_state:
        st.session_state.doc_user_select = False  # Initialize the value if it doesn't exist

    left, middle, right = st.columns([3, 1, 0.5])

    with left:
        st.markdown(
            "<div style='font-size: 18px'><b>Use the checkbox below to generate technical documentation for the proposed GCP solution</b></div>",  # noqa
            unsafe_allow_html=True)
        st.divider()
        st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
        select_doc = st.checkbox(
            "Check this box to generate documentation",
            key="doc",
        )
        # Only update the session state when the checkbox value changes
        if select_doc != st.session_state.doc_user_select:
            st.session_state.doc_user_select = select_doc
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        if st.session_state.doc_user_select:
            st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
            if st.button(label="⟳ Retry", key="retry-doc", type="secondary"):
                st.session_state.doc_user_select = True  # Probably redundant
            st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.doc_user_select:
        doc_prompt = """
            For the given solution, generate a complete, professional technical documentation including a table of contents, 
            for the following GCP architecture. Expand all the table of contents topics to create a comprehensive professional technical documentation
        """  # noqa

        st.session_state.doc_messages.append({"role": "user", "content": doc_prompt})
        doc_messages.append({"role": "user", "content": doc_prompt})

        doc_response, stop_reason = invoke_vertex_ai_model_streaming(doc_messages)
        st.session_state.doc_messages.append({"role": "assistant", "content": doc_response})

        with st.container(height=350):
            st.markdown(doc_response)

        GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME") or "your-gcs-bucket"
        st.session_state.interaction.append({"type": "Technical documentation", "details": doc_response})
        store_in_gcs(content=doc_response, content_type='documentation', bucket_name=GCS_BUCKET_NAME, storage_client=storage_client)
        save_conversation_gcp(st.session_state['conversation_id'], doc_prompt, doc_response, firestore_client)
        collect_feedback_gcp(str(uuid.uuid4()), doc_response, "generate_documentation", GCP_PROJECT)
