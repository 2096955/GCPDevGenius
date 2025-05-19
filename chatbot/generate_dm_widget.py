import os
import streamlit as st
import get_code_from_markdown
from google.cloud import storage, firestore
from utils import (
    invoke_vertex_ai_model_streaming,
    retrieve_environment_variables,
    store_in_gcs,
    save_conversation_gcp,
    collect_feedback_gcp,
    init_gcp_clients,
)
import uuid

# GCP Project and credentials
GCP_PROJECT = retrieve_environment_variables("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
GCP_REGION = retrieve_environment_variables("GOOGLE_CLOUD_REGION", "us-central1")

# Initialize GCP clients using our utility function (which handles mock clients)
storage_client, firestore_client = init_gcp_clients()

# Generate GCP Deployment Manager Template
@st.fragment
def generate_deployment_manager(dm_messages):
    dm_messages = dm_messages[:]
    if 'dm_messages' not in st.session_state:
        st.session_state.dm_messages = []
    if 'dm_user_select' not in st.session_state:
        st.session_state.dm_user_select = None
    left, middle, right = st.columns([4, 0.5, 0.5])
    with left:
        st.markdown(
            "<div style='font-size: 18px'><b>Use the checkbox below to generate a GCP Deployment Manager Template to deploy the proposed solution as Infrastructure as Code</b></div>",  # noqa
            unsafe_allow_html=True)
        st.divider()
        st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
        select_dm = st.checkbox(
            "Check this box to generate GCP Deployment Manager Template",
            key="dm"
        )
        if select_dm != st.session_state.dm_user_select:
            st.session_state.dm_user_select = select_dm
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        if st.session_state.dm_user_select:
            st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
            if st.button(label="⟳ Retry", key="retry-dm", type="secondary"):
                st.session_state.dm_user_select = True
            st.markdown("</div>", unsafe_allow_html=True)
    if st.session_state.dm_user_select:
        dm_prompt = """
            For the given solution, generate a Deployment Manager template in YAML to automate the deployment of GCP resources.
            Provide the actual source code for all the jobs wherever applicable.
            The Deployment Manager template should provision all the resources and the components.
            If Python code is needed, generate a "Hello, World!" code example.
            At the end generate sample commands to deploy the Deployment Manager template.
        """
        dm_messages.append({"role": "user", "content": dm_prompt})
        dm_response, stop_reason = invoke_vertex_ai_model_streaming(dm_messages)
        st.session_state.dm_messages.append({"role": "assistant", "content": dm_response})
        dm_yaml = get_code_from_markdown.get_code_from_markdown(dm_response, language="yaml")[0]
        with st.container(height=350):
            st.markdown(dm_response)
        GCS_BUCKET_NAME = retrieve_environment_variables("GCS_BUCKET_NAME", "gcp-devgenius-assets")
        st.session_state.interaction.append({"type": "Deployment Manager Template", "details": dm_response})
        store_in_gcs(content=dm_response, content_type='deployment_manager', bucket_name=GCS_BUCKET_NAME, storage_client=storage_client)
        save_conversation_gcp(st.session_state['conversation_id'], dm_prompt, dm_response, firestore_client)
        collect_feedback_gcp(str(uuid.uuid4()), dm_response, "generate_dm", GCP_PROJECT)
        object_name = f"{st.session_state['conversation_id']}/template.yaml"
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(object_name)
        blob.upload_from_string(dm_yaml)
        template_object_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{object_name}"
        st.write("Click the below button to deploy the generated solution in your GCP project")
        st.markdown(f"[Download Deployment Manager Template]({template_object_url})") 