import os
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union

from .base_agent import BaseAgent
from ..common import TaskSendParams, AgentSkill

# We'll implement Gemini API integration later
# For now, we'll use a mock implementation
from ...gemini import GeminiAIProvider

logger = logging.getLogger(__name__)

class CodeConversionAgent(BaseAgent):
    """Agent for converting code between different languages and frameworks."""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model_name: str = "gemini-1.5-pro",
                 base_url: str = "http://localhost:8001",
                 host: str = "0.0.0.0",
                 port: int = 8001,
                 log_level: str = "info",
                 **kwargs):
        """Initialize code conversion agent.
        
        Args:
            api_key: Gemini API key (default: from environment variable)
            model_name: Gemini model name
            base_url: Base URL for the agent's A2A service
            host: Host to listen on
            port: Port to listen on
            log_level: Logging level
            **kwargs: Additional arguments to pass to BaseAgent
        """
        # Get API key from environment variable if not provided
        if api_key is None:
            api_key = os.environ.get("GOOGLE_API_KEY")
        
        # Set up Gemini client
        self.gemini = GeminiAIProvider(api_key=api_key, model_name=model_name)
        
        # Define skills
        code_conversion_skills = [
            AgentSkill(
                id="aws-to-gcp",
                name="AWS to GCP Code Conversion",
                description="Convert AWS-specific code to GCP-equivalent code",
                tags=["code", "conversion", "aws", "gcp"],
                examples=[
                    "Convert this AWS Lambda function to a Google Cloud Function",
                    "Translate this AWS CDK code to Terraform for GCP",
                    "How do I migrate this S3 code to use Google Cloud Storage?"
                ]
            ),
            AgentSkill(
                id="general-code-conversion",
                name="General Code Conversion",
                description="Convert code between different languages and frameworks",
                tags=["code", "conversion", "language", "framework"],
                examples=[
                    "Convert this Python code to JavaScript",
                    "How would I implement this Java class in TypeScript?",
                    "Rewrite this React component in Vue"
                ]
            ),
            AgentSkill(
                id="code-refactoring",
                name="Code Refactoring",
                description="Refactor code for better readability, maintainability, or performance",
                tags=["code", "refactoring", "optimization"],
                examples=[
                    "Refactor this function to be more efficient",
                    "Improve the readability of this code",
                    "Optimize this algorithm"
                ]
            )
        ]
        
        # Initialize base agent
        super().__init__(
            name="Code Conversion Agent",
            description="An agent specializing in converting code between different languages, frameworks, and cloud platforms.",
            base_url=base_url,
            version="1.0.0",
            supports_streaming=True,
            supports_push_notifications=False,
            provider_name="DevGenius",
            provider_url="https://devgenius.ai",
            documentation_url="https://devgenius.ai/docs/code-conversion-agent",
            skills=code_conversion_skills,
            input_modes=["text"],
            output_modes=["text"],
            host=host,
            port=port,
            log_level=log_level,
            **kwargs
        )
    
    async def _process_message(self, message: str, params: TaskSendParams) -> str:
        """Process a code conversion request."""
        try:
            # Detect the type of conversion requested
            if "aws" in message.lower() and "gcp" in message.lower():
                # AWS to GCP conversion
                prompt = self._create_aws_to_gcp_prompt(message)
            else:
                # General code conversion
                prompt = self._create_general_conversion_prompt(message)
            
            # Call Gemini to process the prompt
            response = await self.gemini.generate_text(prompt)
            
            return response
        except Exception as e:
            logger.exception(f"Error processing code conversion request: {e}")
            return f"Error processing code conversion request: {str(e)}"
    
    def _create_aws_to_gcp_prompt(self, message: str) -> str:
        """Create a prompt for AWS to GCP code conversion."""
        return f"""As a specialized code conversion expert, please convert the following AWS code to Google Cloud Platform (GCP) equivalent.
Focus on maintaining the same functionality while using GCP-native services and best practices.

AWS CODE/DESCRIPTION:
{message}

Please provide:
1. The GCP equivalent code
2. A brief explanation of the changes
3. Any important considerations or limitations in the conversion

Make sure to handle service mappings like:
- AWS Lambda → Google Cloud Functions/Cloud Run
- Amazon S3 → Google Cloud Storage
- DynamoDB → Firestore/Spanner
- API Gateway → Cloud Endpoints/API Gateway
- CloudFormation/CDK → Deployment Manager/Terraform
- CloudWatch → Cloud Monitoring/Logging
- IAM → IAM
- Cognito → Firebase Authentication/Identity Platform
- SQS → Pub/Sub
- ECS/Fargate → Cloud Run

Output the GCP code with appropriate comments and explanations:
"""
    
    def _create_general_conversion_prompt(self, message: str) -> str:
        """Create a prompt for general code conversion."""
        return f"""As a specialized code conversion expert, please analyze and convert the following code according to the request.
Focus on maintaining the same functionality while following best practices in the target language/framework.

REQUEST:
{message}

Please provide:
1. The converted code
2. A brief explanation of the changes
3. Any important considerations or limitations in the conversion

Output the converted code with appropriate comments and explanations:
""" 