import streamlit as st
from utils import (
    store_in_gcs,
    save_conversation_gcp,
    collect_feedback_gcp,
    invoke_vertex_ai_model_streaming,
    retrieve_environment_variables,
    init_gcp_clients,
)
import uuid
from styles import apply_custom_styles
from google.cloud import storage, firestore
from google.oauth2 import service_account
import os

# GCP Project and credentials
GCP_PROJECT = retrieve_environment_variables("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
GCP_REGION = retrieve_environment_variables("GOOGLE_CLOUD_REGION", "us-central1")
storage_client, firestore_client = init_gcp_clients()

# Generate Cost Estimates
@st.fragment
def generate_cost_estimates(cost_messages):
    apply_custom_styles()
    cost_messages = cost_messages[:]
    if 'cost_messages' not in st.session_state:
        st.session_state.cost_messages = []
    if 'cost_user_select' not in st.session_state:
        st.session_state.cost_user_select = False
    concatenated_message = ' '.join(
        message['content'] for message in cost_messages if message['role'] == 'assistant'
    )
    left, middle, right = st.columns([3, 1, 0.5])
    
    # Apply additional immediate styling to guarantee readability
    st.markdown("""
    <style>
    /* Cost estimate specific styles */
    .cost-header, .cost-content, .cost-button, .cost-response {
        background-color: white !important;
        color: black !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 5px !important;
        padding: 10px !important;
        margin-bottom: 10px !important;
    }
    
    .cost-header {
        font-size: 18px !important;
        font-weight: bold !important; 
    }
    
    /* Force rendering of tables with white bg and black text */
    .cost-response table, .cost-response th, .cost-response td,
    .cost-response tr, .cost-response tbody, .cost-response thead {
        background-color: white !important;
        color: black !important;
        border: 1px solid #e0e0e0 !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with left:
        st.markdown(
            """<div class="cost-header">
            Use the checkbox below to get cost estimates of GCP services in the proposed solution
            </div>""",
            unsafe_allow_html=True)
        st.divider()
        st.markdown("""<div class="cost-content">""", unsafe_allow_html=True)
        select_cost = st.checkbox(
            "Check this box to get the cost estimates",
            key="cost",
        )
        if select_cost != st.session_state.cost_user_select:
            st.session_state.cost_user_select = select_cost
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        if st.session_state.cost_user_select:
            st.markdown('<div class="cost-button">', unsafe_allow_html=True)
            if st.button(label="⟳ Retry", key="retry-cost", type="secondary"):
                st.session_state.cost_user_select = True
            st.markdown("</div>", unsafe_allow_html=True)
    if st.session_state.cost_user_select:
        cost_prompt = f"""
            Calculate approximate monthly cost for the generated architecture based on the following description:
            {concatenated_message}
            Use https://cloud.google.com/products/calculator and https://cloud.google.com/pricing/list for getting the latest GCP pricing.
            Provide a short summary for easier consumption in a tabular format - service name, configuration size, price, and total cost.
            Order the services by the total cost in descending order while displaying the tabular format.
            The tabular format should look **very professional and readable**, with a clear structure that is easy to interpret. 
            Ensure that the services are ordered by **Total Cost** in descending order to highlight the most expensive services first.
            Use the below example as reference to generate the pricing details in tabular output format.
            <example>
            Based on the architecture described and using the latest GCP pricing information, here's an approximate monthly cost breakdown for the enterprise data lake solution. Please note that these are estimates and actual costs may vary based on usage, data transfer, and other factors.

| Service Name | Configuration | Price (per unit) | Estimated Monthly Cost |
|--------------|---------------|-------------------|------------------------|
| Google Cloud Run | 2 services, 0.25 vCPU, 0.5 GB RAM, running 24/7 | $0.024 per vCPU-hour | $43.20 |
| Google Vertex AI | 1 n1-standard-4, 10 GB storage | $0.50 per hour + $0.026 per GB-month | $40.00 |
| Google Cloud Storage | 100 GB storage, 100 GB data transfer | $0.020 per GB-month + $0.12 per GB transfer | $32.00 |
| Google Cloud CDN | 100 GB data transfer, 1M requests | $0.08 per GB + $0.007 per 10,000 requests | $8.70 |
| Google Load Balancer | 1 LB, running 24/7 | $0.025 per hour | $18.00 |
| Google Firestore | 25 GB storage, 1M write requests, 1M read requests | $0.18 per GB-month + $0.18 per million write requests + $0.06 per million read requests | $6.00 |
| Google Cloud Functions | 1M invocations, 128 MB memory, 100ms avg. duration | $0.40 per 1M requests + $0.0000025 per GB-second | $0.35 |
| Google Cloud Monitoring | 5 GB logs ingested, 5 custom metrics | $0.50 per GB ingested + $0.30 per metric per month | $3.00 |
| Google VPC | 1 NAT Gateway, running 24/7 | $0.045 per hour + $0.045 per GB processed | $32.40 |
| Total Estimated Monthly Cost | | | $183.65 |

Please note:
1. These estimates assume moderate usage and may vary based on actual workload.
2. Data transfer costs between services within the same region are not included, as they are typically free.
3. Costs for Terraform, Deployment Manager, and IAM are not included as they are generally free services.
4. The Vertex AI and custom model costs are not included as pricing information for these services was not available at the time of this estimation.
5. Actual costs may be lower with committed use discounts or other discounts available to your GCP account.
        """
        cost_messages.append({"role": "user", "content": cost_prompt})
        cost_response, stop_reason = invoke_vertex_ai_model_streaming(cost_messages)
        cost_response = cost_response.replace("$", "USD ")
        st.session_state.cost_messages.append({"role": "assistant", "content": cost_response})
        with st.container(height=350):
            st.markdown('<div class="cost-response">', unsafe_allow_html=True)
            st.markdown(cost_response, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME") or "your-gcs-bucket"
        st.session_state.interaction.append({"type": "Cost Analysis", "details": cost_response})
        store_in_gcs(content=cost_response, content_type='cost', bucket_name=GCS_BUCKET_NAME, storage_client=storage_client)
        save_conversation_gcp(st.session_state['conversation_id'], cost_prompt, cost_response, firestore_client)
        collect_feedback_gcp(str(uuid.uuid4()), cost_response, "generate_cost", GCP_PROJECT)
