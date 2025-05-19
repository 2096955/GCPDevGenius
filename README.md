# DevGenius GCP Solution Builder

A smart, AI-powered solution architect that helps design, document, and generate infrastructure-as-code on GCP. This was inspired by https://github.com/aws-samples/sample-devgenius-aws-solution-builder (Due credit to Prasanna Sridharan of AWS for the inspiration)

## Features

- **Interactive Chatbot Interface**: Design GCP architectures through natural language conversations
- **Architecture Visualization**: Generate architecture diagrams for your GCP solutions
- **Infrastructure as Code Generation**: Create Terraform, Deployment Manager, and CDK templates
- **Cost Estimation**: Get estimated costs for your designed GCP architecture
- **Technical Documentation**: Generate comprehensive documentation for your solutions
- **Local Storage**: Save conversations and feedback to local files for reference

## Setup Instructions

### Prerequisites
- Python 3.10+
- Node.js 16+ (for CDK support)
- Google Cloud Platform account with required APIs enabled
- Service account with appropriate permissions

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/sample-devgenius-aws-solution-builder.git
cd sample-devgenius-aws-solution-builder
```

2. Set up Python virtual environment:
```bash
python -m venv chatbot_venv
source chatbot_venv/bin/activate  # On Windows: chatbot_venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r chatbot/requirements.txt
```

4. Create environment file:
```bash
cp .env.example .env
```

5. Update the `.env` file with your Google Cloud Platform credentials.

### Running the Application

Start the Streamlit application:
```bash
cd chatbot
python -m streamlit run agent.py
```

The application will be available at http://localhost:8501

## Architecture

The solution consists of:

- **Streamlit Frontend**: User interface for interacting with the solution
- **Vertex AI Integration**: Powers the conversational AI
- **Local Storage**: JSON-based storage for conversations and feedback
- **Google Cloud Integration**: Connects with Google Cloud services
- **A2A Framework**: Agent-to-agent communication (optional)

## Known Issues & Limitations

- A2A functionality requires additional setup and dependencies
- Some Firestore operations may fail if not properly configured
- The service requires appropriate GCP service account permissions

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
