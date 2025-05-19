import uuid
import get_code_from_markdown
import streamlit as st
from utils import (
    invoke_vertex_ai_model_streaming,
    store_in_gcs,
    save_conversation_gcp,
    collect_feedback_gcp,
    retrieve_environment_variables,
    init_gcp_clients,
)
from google.cloud import storage, firestore
from google.oauth2 import service_account
import os

# GCP Project and credentials
GCP_PROJECT = retrieve_environment_variables("GOOGLE_CLOUD_PROJECT", "your-gcp-project-id")
GCP_REGION = retrieve_environment_variables("GOOGLE_CLOUD_REGION", "us-central1")

# Initialize GCP clients using our utility function (which handles mock clients)
storage_client, firestore_client = init_gcp_clients()

@st.fragment
def generate_arch(arch_messages):
    arch_messages = arch_messages[:]
    if 'arch_messages' not in st.session_state:
        st.session_state.arch_messages = []
    if 'arch_user_select' not in st.session_state:
        st.session_state.arch_user_select = False
    left, middle, right = st.columns([3, 1, 0.5])
    with left:
        st.markdown(
            "<div style='font-size: 18px'><b>Use the checkbox below to generate a visual representation of the proposed GCP solution</b></div>",  # noqa
            unsafe_allow_html=True)
        st.divider()
        st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
        select_arch = st.checkbox(
            "Check this box to generate architecture",
            key="arch"
        )
        if select_arch != st.session_state.arch_user_select:
            st.session_state.arch_user_select = select_arch
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        if st.session_state.arch_user_select:
            st.markdown("<div class=stButton gen-style'>", unsafe_allow_html=True)
            if st.button(label="⟳ Retry", key="retry", type="secondary"):
                st.session_state.arch_user_select = True
            st.markdown("</div>", unsafe_allow_html=True)
    if st.session_state.arch_user_select:
        architecture_prompt = """
            Generate a GCP architecture and data flow diagram for the given solution, applying GCP best practices. Follow these steps:
            1. Create an XML file suitable for draw.io that captures the architecture and data flow.
            2. Reference the latest GCP architecture icons here: https://cloud.google.com/architecture/icons, Always use the latest GCP icons for generating the architecture.
            3. Respond only with the XML in markdown format—no additional text.
            4. Ensure the XML is complete, with all elements having proper opening and closing tags.
            5. Confirm that all GCP services/icons are properly connected and enclosed within a GCP Cloud icon, deployed inside a VPC where applicable.
            6. Remove unnecessary whitespace to optimize size and minimize output tokens.
            7. Use valid GCP architecture icons to represent services, avoiding random images.
            8. Please ensure the architecture diagram is clearly defined, neatly organized, and highly readable. The flow should be visually clean, with all arrows properly connected without overlaps. If non-GCP services like on-premises databases, servers, or external systems are included, use appropriate generic icons from draw.io to represent them. The final diagram should look polished, professional, and easy to understand at a glance.
            9. Please create a clearly structured and highly readable architecture diagram. Arrange all GCP service icons and non-GCP components (use generic draw.io icons for on-premises servers, databases, etc.) in a way that is clean, visually aligned, and properly spaced. Ensure arrows are straight, not overlapped or tangled, and clearly indicate the flow without crossing over service icons. Maintain enough spacing between elements to avoid clutter. The overall diagram should look professional, polished, and the data flow must be immediately understandable at a glance.
            10. The final XML should be syntactically correct and cover all components of the given solution.
        """
        st.session_state.arch_messages.append({"role": "user", "content": architecture_prompt})
        arch_messages.append({"role": "user", "content": architecture_prompt})
        max_attempts = 4
        full_response_array = []
        full_response = ""
        for attempt in range(max_attempts):
            arch_gen_response, stop_reason = invoke_vertex_ai_model_streaming(arch_messages, enable_reasoning=True)
            full_response_array.append(arch_gen_response)
            if stop_reason != "max_tokens":
                break
            if attempt == 0:
                full_response = ''.join(str(x) for x in full_response_array)
                arch_messages = continuation_prompt(architecture_prompt, full_response)
        if attempt == max_attempts - 1:
            st.error("Reached maximum number of attempts. Final result is incomplete. Please try again.")
        try:
            full_response = ''.join(str(x) for x in full_response_array)
            arch_content_xml = get_code_from_markdown.get_code_from_markdown(full_response, language="xml")[0]
            # Optionally convert XML to HTML for preview (if you have a util for this)
            # arch_content_html = convert_xml_to_html(arch_content_xml)
            st.session_state.arch_messages.append({"role": "assistant", "content": "XML"})
            with st.container():
                st.code(arch_content_xml, language="xml")
            st.session_state.interaction.append({"type": "Solution Architecture", "details": full_response})
            store_in_gcs(content=full_response, content_type='architecture', bucket_name="your-gcs-bucket", storage_client=storage_client)
            save_conversation_gcp(st.session_state['conversation_id'], architecture_prompt, full_response, firestore_client)
            collect_feedback_gcp(str(uuid.uuid4()), arch_content_xml, "generate_architecture", GCP_PROJECT)
        except Exception as e:
            st.error("Internal error occurred. Please try again.")
            print(f"Error occurred when generating architecture: {str(e)}")
            del st.session_state.arch_messages[-1]
            del arch_messages[-1]
