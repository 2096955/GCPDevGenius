import os
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union

from .base_agent import BaseAgent
from ..common import TaskSendParams, AgentSkill, TaskState, Artifact, TextPart

# Import the Gemini provider
from ...gemini import GeminiAIProvider

logger = logging.getLogger(__name__)

class DataMigrationAgent(BaseAgent):
    """Agent for data model conversion and migration between AWS and GCP."""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 model_name: str = "gemini-1.5-pro",
                 base_url: str = "http://localhost:8002",
                 host: str = "0.0.0.0",
                 port: int = 8002,
                 log_level: str = "info",
                 **kwargs):
        """Initialize data migration agent.
        
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
        data_migration_skills = [
            AgentSkill(
                id="dynamodb-to-firestore",
                name="DynamoDB to Firestore Migration",
                description="Convert DynamoDB data model to Firestore",
                tags=["data", "migration", "aws", "gcp", "dynamodb", "firestore"],
                examples=[
                    "Convert this DynamoDB table schema to Firestore",
                    "How should I migrate this DynamoDB data to Firestore?",
                    "What's the equivalent of this DynamoDB query in Firestore?"
                ]
            ),
            AgentSkill(
                id="dynamodb-to-spanner",
                name="DynamoDB to Spanner Migration",
                description="Convert DynamoDB data model to Spanner",
                tags=["data", "migration", "aws", "gcp", "dynamodb", "spanner"],
                examples=[
                    "Convert this DynamoDB table schema to Spanner",
                    "How should I migrate this DynamoDB data to Spanner?",
                    "What's the equivalent of this DynamoDB query in Spanner SQL?"
                ]
            ),
            AgentSkill(
                id="s3-to-gcs",
                name="S3 to GCS Migration",
                description="Convert S3 storage configurations to Google Cloud Storage",
                tags=["data", "migration", "aws", "gcp", "s3", "gcs"],
                examples=[
                    "How do I migrate this S3 bucket configuration to GCS?",
                    "What's the equivalent of this S3 lifecycle policy in GCS?",
                    "Convert this S3 IAM policy to GCS equivalent"
                ]
            ),
            AgentSkill(
                id="rds-to-cloudsql",
                name="RDS to Cloud SQL Migration",
                description="Migrate from Amazon RDS to Google Cloud SQL",
                tags=["data", "migration", "aws", "gcp", "rds", "cloudsql"],
                examples=[
                    "How do I migrate my RDS MySQL database to Cloud SQL?",
                    "What are the steps to convert this RDS PostgreSQL schema to Cloud SQL?",
                    "Generate a migration plan from RDS to Cloud SQL"
                ]
            ),
            AgentSkill(
                id="data-validation",
                name="Data Validation",
                description="Validate data consistency during migration",
                tags=["data", "validation", "migration", "aws", "gcp"],
                examples=[
                    "How can I validate my data after migration from DynamoDB to Firestore?",
                    "Generate a data validation script for S3 to GCS migration",
                    "Create a plan to verify data integrity after migration"
                ]
            )
        ]
        
        # Initialize base agent
        super().__init__(
            name="Data Migration Agent",
            description="An agent specializing in data model conversion and migration between AWS and GCP.",
            base_url=base_url,
            version="1.0.0",
            supports_streaming=True,
            supports_push_notifications=False,
            provider_name="DevGenius",
            provider_url="https://devgenius.ai",
            documentation_url="https://devgenius.ai/docs/data-migration-agent",
            skills=data_migration_skills,
            input_modes=["text"],
            output_modes=["text"],
            host=host,
            port=port,
            log_level=log_level,
            **kwargs
        )
    
    async def _process_message(self, message: str, params: TaskSendParams) -> str:
        """Process a data migration request."""
        try:
            # Detect the type of data migration requested
            if "dynamodb" in message.lower() and "firestore" in message.lower():
                prompt = self._create_dynamodb_to_firestore_prompt(message)
            elif "dynamodb" in message.lower() and "spanner" in message.lower():
                prompt = self._create_dynamodb_to_spanner_prompt(message)
            elif "s3" in message.lower() and ("gcs" in message.lower() or "cloud storage" in message.lower()):
                prompt = self._create_s3_to_gcs_prompt(message)
            elif "rds" in message.lower() and ("cloudsql" in message.lower() or "cloud sql" in message.lower()):
                prompt = self._create_rds_to_cloudsql_prompt(message)
            elif "validation" in message.lower() or "verify" in message.lower() or "integrity" in message.lower():
                prompt = self._create_data_validation_prompt(message)
            else:
                # General data migration prompt
                prompt = self._create_general_data_migration_prompt(message)
            
            # Call Gemini to process the prompt
            response = await self.gemini.generate_text(prompt)
            
            # Create artifact with response - could be added in streaming mode
            if params.id and self.supports_streaming:
                artifact = Artifact(
                    name="migration_result",
                    description="Data migration result",
                    parts=[TextPart(text=response)]
                )
                await self.add_artifact(params.id, artifact, final=True)
            
            return response
        except Exception as e:
            logger.exception(f"Error processing data migration request: {e}")
            return f"Error processing data migration request: {str(e)}"
    
    def _create_dynamodb_to_firestore_prompt(self, message: str) -> str:
        """Create a prompt for DynamoDB to Firestore migration."""
        return f"""As a data migration expert specializing in NoSQL database migration from AWS to GCP, please help with the following DynamoDB to Firestore migration.

REQUEST/INFORMATION:
{message}

Please provide:
1. A detailed mapping of the DynamoDB data model to Firestore
2. Schema recommendations leveraging Firestore's document-collection model
3. Code samples for data access in both DynamoDB and equivalent Firestore
4. Migration strategy and best practices
5. Performance considerations and trade-offs

Keep in mind the following key differences:
- DynamoDB uses tables with items, while Firestore uses collections with documents
- DynamoDB has a primary key (partition + optional sort), while Firestore uses document IDs
- DynamoDB has strongly consistent reads, while Firestore has strong consistency by default
- Firestore has hierarchical data model with subcollections, while DynamoDB is flat
- Query capabilities differ significantly between the two databases
- Transactions work differently in both systems
- Capacity provisioning and pricing models are different

Format your response with clear examples, code snippets, and structured recommendations:
"""
    
    def _create_dynamodb_to_spanner_prompt(self, message: str) -> str:
        """Create a prompt for DynamoDB to Spanner migration."""
        return f"""As a data migration expert specializing in database migration from AWS to GCP, please help with the following DynamoDB to Spanner migration.

REQUEST/INFORMATION:
{message}

Please provide:
1. A detailed mapping of the DynamoDB data model to Spanner's relational model
2. Schema recommendations including table design, interleaved tables, and foreign keys
3. Code samples for data access in both DynamoDB and equivalent Spanner SQL
4. Migration strategy and best practices
5. Performance considerations and trade-offs

Keep in mind the following key differences:
- DynamoDB is NoSQL, while Spanner is a distributed relational database
- DynamoDB uses tables with items, while Spanner uses relational tables with rows
- DynamoDB has a primary key (partition + optional sort), while Spanner has primary keys and interleaved tables
- DynamoDB has eventually consistent reads by default, while Spanner is strongly consistent
- Spanner supports SQL queries, transactions, and relational constraints
- Capacity provisioning and pricing models are different

Format your response with clear examples, code snippets, and structured recommendations:
"""
    
    def _create_s3_to_gcs_prompt(self, message: str) -> str:
        """Create a prompt for S3 to GCS migration."""
        return f"""As a data migration expert specializing in cloud storage migration from AWS to GCP, please help with the following S3 to Google Cloud Storage migration.

REQUEST/INFORMATION:
{message}

Please provide:
1. A detailed mapping of S3 concepts to GCS equivalents
2. Configuration recommendations for GCS buckets, objects, and access control
3. Code samples for object operations in both S3 and equivalent GCS
4. Migration strategy and best practices
5. Performance considerations and trade-offs

Keep in mind the following key differences:
- S3 uses IAM roles and policies, while GCS uses IAM roles and ACLs
- S3 has bucket policies, while GCS has IAM conditions and ACLs
- S3 has transfer acceleration, while GCS has different transfer options
- Lifecycle management configuration differs between services
- Consistency models differ (S3 is eventually consistent for some operations)
- Storage class options and pricing models are different

Format your response with clear examples, code snippets, and structured recommendations:
"""
    
    def _create_rds_to_cloudsql_prompt(self, message: str) -> str:
        """Create a prompt for RDS to Cloud SQL migration."""
        return f"""As a data migration expert specializing in relational database migration from AWS to GCP, please help with the following RDS to Cloud SQL migration.

REQUEST/INFORMATION:
{message}

Please provide:
1. A detailed migration plan from RDS to Cloud SQL
2. Configuration recommendations for Cloud SQL instance
3. Instructions for schema and data migration
4. Code samples for connectivity and access in both RDS and Cloud SQL
5. Performance considerations and trade-offs

Keep in mind the following key differences:
- RDS and Cloud SQL have different instance types and configuration options
- Connection methods and security settings differ
- Backup, maintenance, and high availability configurations vary
- Some database features may be supported on one platform but not the other
- Capacity provisioning and pricing models are different

Format your response with clear examples, code snippets, and structured recommendations:
"""
    
    def _create_data_validation_prompt(self, message: str) -> str:
        """Create a prompt for data validation during migration."""
        return f"""As a data migration validation expert, please help with the following data validation request for AWS to GCP migration.

REQUEST/INFORMATION:
{message}

Please provide:
1. A comprehensive data validation strategy
2. Specific validation techniques and tools for the migration scenario
3. Code samples for validation scripts where appropriate
4. Best practices for ensuring data integrity during and after migration
5. Recommendations for handling discrepancies and validation failures

The validation strategy should include:
- Source and target count validation
- Schema and data type validation
- Data content sampling and comparison
- Performance and load testing
- Logging and reporting of validation results
- Rollback procedures if validation fails

Format your response with clear examples, code snippets, and structured recommendations:
"""
    
    def _create_general_data_migration_prompt(self, message: str) -> str:
        """Create a prompt for general data migration."""
        return f"""As a data migration expert specializing in AWS to GCP migration, please help with the following data migration request.

REQUEST/INFORMATION:
{message}

Please provide:
1. Analysis of the migration requirements and source/target systems
2. A detailed migration strategy and approach
3. Recommendations for tools and methods based on the data types and volumes
4. Code or configuration examples where appropriate
5. Best practices and considerations for this specific migration

Consider the following aspects:
- Compatibility between source and target systems
- Data model and schema mapping
- Migration methodologies (online vs. offline, bulk vs. incremental)
- Downtime requirements and impact on existing systems
- Validation and verification approaches
- Post-migration operations and monitoring

Format your response with clear examples, code snippets, and structured recommendations:
""" 