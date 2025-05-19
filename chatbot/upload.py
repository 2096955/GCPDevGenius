import streamlit as st
from google.cloud import storage, firestore
from google.oauth2 import service_account
import os
import uuid
from pypdf import PdfWriter, PdfReader
import io
import tempfile
# Import necessary modules
from langchain.document_loaders import UnstructuredPowerPointLoader

# GCP environment variables
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") or "gbg-neuro"
GCP_REGION = os.getenv("GOOGLE_CLOUD_REGION") or "us-central1"
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME") or "devgenius-files"

import re

class PPTExtraction:
    def __init__(self, file_path):
        """
        Initialize PPTExtraction class with the provided file path.

        Args:
        - file_path (str): Path to the PowerPoint file.
        """
        self.file_path = file_path
        # Initialize the UnstructuredPowerPointLoader to load PowerPoint data.
        self.loader = UnstructuredPowerPointLoader(self.file_path, mode="elements")
        # Load the PowerPoint data.
        self.data = self.loader.load()

    def extract(self):
        """
        Extract text content from the PowerPoint slides and format them.

        Returns:
        - str: Formatted text containing the extracted content.
        """
        slides = []
        current_slide_number = None

        # Iterate through each document in the PowerPoint data.
        for document in self.data:
            # Check the category of the current document.
            if document.metadata["category"] == "Title":
                slide_number = document.metadata["page_number"]
                # If the slide number changes, format the slide accordingly.
                if slide_number != current_slide_number:
                    if slide_number == 1:
                        slide = f"Slide {slide_number}:\n\nTitle: {document.page_content}"
                    else:
                        slide = f"Slide {slide_number}:\n\nOutline: {document.page_content}"
                    current_slide_number = slide_number
                else:
                    slide = f"Outline: {document.page_content}"
            elif document.metadata["category"] in ["NarrativeText", "ListItem"]:
                slide = f"Content: {document.page_content}"
            elif document.metadata["category"] == "PageBreak":
                # If it's a page break, reset the current slide number.
                slide = ""
                current_slide_number = None
            else:
                continue

            slides.append(slide)

        # Join the formatted slides into a single string.
        formatted_slides = "\n\n".join(slides)
        return formatted_slides


def split_pdf(pdf_content):
    pdf_reader = PdfReader(io.BytesIO(pdf_content))
    total_pages = len(pdf_reader.pages)
    mid_point = total_pages // 2

    # Create two new PDF writers
    part1_writer = PdfWriter()
    part2_writer = PdfWriter()

    # Split pages between the two writers
    for page_num in range(total_pages):
        if page_num < mid_point:
            part1_writer.add_page(pdf_reader.pages[page_num])
        else:
            part2_writer.add_page(pdf_reader.pages[page_num])

    # Save both parts to bytes objects
    part1_bytes = io.BytesIO()
    part2_bytes = io.BytesIO()

    part1_writer.write(part1_bytes)
    part2_writer.write(part2_bytes)

    return part1_bytes.getvalue(), part2_bytes.getvalue()


def upload_to_gcs(file_content, filename, bucket_name, storage_client):
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(filename)
        
        # If file_content is bytes, upload from string
        if isinstance(file_content, bytes):
            blob.upload_from_string(file_content)
        else:
            # Create a temporary file and upload from it
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                temp.write(file_content)
                temp_path = temp.name
            
            blob.upload_from_filename(temp_path)
            os.unlink(temp_path)  # Delete the temporary file
            
        return True, blob.public_url
    except Exception as e:
        st.error(f"Error uploading to GCS: {str(e)}")
        return False, None


def upload_file_to_gcs(uploaded_file, bucket_name, storage_client):
    blob_name = f"uploads/{uuid.uuid4()}_{uploaded_file.name}"
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_file(uploaded_file)
    return blob.public_url

def save_upload_metadata_gcp(file_url, user_id, firestore_client):
    doc_ref = firestore_client.collection("uploads").document()
    doc_ref.set({
        "file_url": file_url,
        "user_id": user_id,
        "timestamp": firestore.SERVER_TIMESTAMP,
    })

# Initialize GCP clients
def get_gcp_credentials():
    credentials = None
    if os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
        credentials = service_account.Credentials.from_service_account_file(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        )
    return credentials

# Initialize GCP clients
credentials = get_gcp_credentials()
storage_client = storage.Client(project=GCP_PROJECT, credentials=credentials)
firestore_client = firestore.Client(project=GCP_PROJECT, credentials=credentials)

# Streamlit file uploader UI
def file_upload_widget(user_id):
    st.markdown("## Upload a file to Google Cloud Storage")
    uploaded_file = st.file_uploader("Choose a file", type=None)
    if uploaded_file is not None:
        file_url = upload_file_to_gcs(uploaded_file, GCS_BUCKET_NAME, storage_client)
        save_upload_metadata_gcp(file_url, user_id, firestore_client)
        st.success(f"File uploaded successfully! [View file]({file_url})")

