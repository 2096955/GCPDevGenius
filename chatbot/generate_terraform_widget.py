import streamlit as st
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
import get_code_from_markdown
import os

# GCP Project and credentials
GCP_PROJECT = retrieve_environment_variables("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
GCP_REGION = retrieve_environment_variables("GOOGLE_CLOUD_REGION", "us-central1")

# Initialize GCP clients using our utility function (which handles mock clients)
storage_client, firestore_client = init_gcp_clients()

# Generate Terraform
@st.fragment
def generate_terraform(terraform_messages):
    terraform_messages = terraform_messages[:]
    if 'terraform_messages' not in st.session_state:
        st.session_state.terraform_messages = []
    if 'terraform_user_select' not in st.session_state:
        st.session_state.terraform_user_select = False
    left, middle, right = st.columns([3, 1, 0.5])
    with left:
        st.markdown(
            "<div style='font-size: 18px'><b>Use the checkbox below to generate Terraform code as Infrastructure as Code for the proposed GCP solution</b></div>",  # noqa
            unsafe_allow_html=True)
        st.divider()
        st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
        select_terraform = st.checkbox(
            "Check this box to generate Terraform code ",
            key="terraform",
            help="Terraform enables you to define and provision GCP infrastructure using code"
        )
        if select_terraform != st.session_state.terraform_user_select:
            st.session_state.terraform_user_select = select_terraform
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        if st.session_state.terraform_user_select:
            st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
            if st.button(label="⟳ Retry", key="retry-terraform", type="secondary"):
                st.session_state.terraform_user_select = True
            st.markdown("</div>", unsafe_allow_html=True)
    if st.session_state.terraform_user_select:
        terraform_prompt = """
            For the given solution, generate a Terraform script in HCL to automate and deploy the required GCP resources.
            Provide the actual source code for all jobs wherever applicable.
            The Terraform code should provision all resources and components without version restrictions.
            If Python code is needed, generate a \"Hello, World!\" code example.
            At the end generate sample commands to deploy the Terraform code.
        """
        st.session_state.terraform_messages.append({"role": "user", "content": terraform_prompt})
        terraform_messages.append({"role": "user", "content": terraform_prompt})
        terraform_response, stop_reason = invoke_vertex_ai_model_streaming(terraform_messages)
        st.session_state.terraform_messages.append({"role": "assistant", "content": terraform_response})
        with st.container(height=350):
            st.markdown(terraform_response)
        GCS_BUCKET_NAME = retrieve_environment_variables("GCS_BUCKET_NAME", "gcp-devgenius-assets")
        st.session_state.interaction.append({"type": "Terraform Template", "details": terraform_response})
        store_in_gcs(content=terraform_response, content_type='terraform', bucket_name=GCS_BUCKET_NAME, storage_client=storage_client)
        save_conversation_gcp(st.session_state['conversation_id'], terraform_prompt, terraform_response, firestore_client)
        collect_feedback_gcp(str(uuid.uuid4()), terraform_response, "generate_terraform", GCP_PROJECT)
        tf_code = get_code_from_markdown.get_code_from_markdown(terraform_response, language="hcl")[0]
        object_name = f"{st.session_state['conversation_id']}/main.tf"
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(object_name)
        blob.upload_from_string(tf_code)
        template_object_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{object_name}"
        st.write("Click the below button to download the generated Terraform code for your GCP project")
        st.markdown(f"[Download Terraform main.tf]({template_object_url})") 