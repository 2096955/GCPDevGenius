import streamlit as st


def apply_styles():
    """Apply custom CSS to the Streamlit app."""
    st.markdown("""
    <style>
    /* Adjust the gap between tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        display: flex;
        flex-wrap: wrap; /* Allow wrapping when space is limited */
        justify-content: space-between; /* Distribute tabs evenly */
    }
    /* Style each individual tab */
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: #F0F2F6; /* Light gray background */
        border-radius: 8px 8px 0 0; /* Rounded top corners */
        padding: 12px 24px; /* More padding for better spacing */
        font-size: 16px; /* Slightly larger text */
        font-weight: 600; /* Make the text semi-bold */
        text-align: center;
        transition: background-color 0.3s ease, transform 0.3s ease; /* Smooth transitions */
        cursor: pointer;
        flex: 1;  /* Make tabs grow equally */
        min-width: 0;  /* Allow tabs to shrink if needed */
        margin: 0 1px;  /* Small margin between tabs */
    }
    /* Active tab styles */
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50; /* Green background for active tab */
        color: white; /* White text for active tab */
        transform: translateY(-3px); /* Slight "lift" effect for active tab */
    }
    /* Hover effect for tabs */
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #E8E8E8; /* Light hover effect */
        transform: translateY(-2px); /* Lift effect on hover */
        color: black;
    }
    /* Style for the tab list container */
    .stTabs [data-baseweb="tab-list"] {
        display: flex;
        justify-content: space-evenly; /* Even spacing between tabs */
        margin-bottom: 20px; /* Space between tabs and content */
        width: 100%;  /* Ensure full width */
    }
    /* Adjust the tab content area */
    .stTabs [data-baseweb="tab-panel"] {
        padding: 20px;
        background-color: #fafafa; /* Light background for tab content */
        border-radius: 8px; /* Rounded corners for content */
        box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.1); /* Soft shadow around content */
    }
    /* Text input style */
    .stTextInput > div > input {
        background-color: #f4f4f9;  /* Light background */
        border: 2px solid #0073e6;  /* Blue border */
        border-radius: 12px;  /* Rounded corners */
        font-size: 16px;  /* Font size */
        padding: 10px 15px;  /* Padding inside input box */
        width: 100%;  /* Full width */
        box-sizing: border-box;  /* Prevent overflow issues */
    }
    .stTextInput > div > input:focus {
        outline: none;  /* Remove outline on focus */
        border-color: #005bb5;  /* Darker border on focus */
        box-shadow: 0 0 5px rgba(0, 92, 181, 0.5);  /* Focus effect */
    }
    /* Style the submit button (optional) */
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        border: 2px solid #4CAF50;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 14px;
        cursor: pointer;
    }
    .stButton > button:hover {
        background-color: #4CAF50;  /* Hover effect */
        color: white;
    }
    /* Adjust Chat Input */
    .stChatInput { 
        position: fixed; 
        bottom: 20px; 
        z-index: 10; 
        background-color: lightgrey; 
    }
    /* Responsive Styles: For smaller screen sizes (mobile) */
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab-list"] {
            flex-direction: row; /* Keep tabs in a row, but allow wrapping */
            flex-wrap: wrap; /* Allow the tabs to wrap */
            justify-content: space-evenly; /* Distribute tabs evenly */
        }
        /* Ensure that tabs take up equal space on smaller screens */
        .stTabs [data-baseweb="tab"] {
            font-size: 14px;  /* Smaller text size */
            padding: 10px 12px;    /* Adjust padding for mobile */
            margin: 5px 0;    /* More space between tabs */
            flex-basis: 30%;  /* Allow the tabs to be more flexible */
        }
        .stTabs [data-baseweb="tab-panel"] {
            padding: 15px;    /* Adjust padding for mobile */
        }
        .stTextInput > div > input {
            font-size: 14px;  /* Smaller font size on mobile */
            padding: 8px 12px;  /* Adjust padding for mobile */
        }
        .stButton > button {
            font-size: 12px;   /* Smaller button text */
            padding: 8px 16px; /* Adjust padding for mobile */
        }
    }
    .stButton button {
        background-color: #4285F4; /* GCP blue */
        color: white;
        font-size: 18px;
        padding: 16px 40px;
        border-radius: 8px;
        width: auto;
        text-align: center;
        white-space: nowrap;
        font-weight: bold;
        display: inline-block;
    }
    .gen-style {
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .stSidebar {
        background-color: #f5f5f5;
    }
    /* CHAT ELEMENTS - Ensure high contrast and visibility */
    [data-testid="stChatMessage"] {
        background-color: white !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
        margin-bottom: 10px !important;
        overflow: visible !important;
    }
    /* Style the chat message content */
    [data-testid="stChatMessageContent"] {
        background-color: white !important;
        color: black !important;
        padding: 15px !important;
        border-radius: 5px !important;
        font-size: 16px !important;
    }
    /* User messages */
    [data-testid="stChatMessage"][data-testid*="user"] {
        background-color: #f0f8ff !important; /* Light blue for user */
        border-color: #b3d9ff !important;
    }
    /* Assistant messages */
    [data-testid="stChatMessage"][data-testid*="assistant"] {
        background-color: #f9f9f9 !important; /* Light gray for assistant */
        border-color: #d9d9d9 !important;
    }
    /* Force text color to be black for all text in chat */
    [data-testid="stChatMessage"] p, 
    [data-testid="stChatMessage"] span, 
    [data-testid="stChatMessage"] div,
    [data-testid="stChatMessage"] code,
    [data-testid="stChatMessage"] pre {
        color: black !important;
        background-color: transparent !important;
    }
    /* Ensure chat input has visible text */
    .stChatInput input {
        color: black !important;
        background-color: white !important;
        border: 2px solid #4285F4 !important;
        padding: 12px !important;
        border-radius: 8px !important;
        font-size: 16px !important;
    }
    </style>
    """, unsafe_allow_html=True)


def apply_custom_styles():
    """Apply custom CSS to the Streamlit app."""
    st.markdown("""
    <style>
        /* Style the button (optional) */
        .stButton button {
            background-color: #34A853; /* GCP green */
            color: white;
            font-size: 16px;
            padding: 12px 32px;
            border-radius: 6px;
            width: auto;
            text-align: center;
            white-space: nowrap;
            font-weight: bold;
            display: inline-block;
        }
        .gen-style {
            margin-top: 8px;
            margin-bottom: 8px;
        }
    </style>
    """, unsafe_allow_html=True)
