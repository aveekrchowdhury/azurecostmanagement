"""LLM-based resource classification service using Azure AI Foundry."""

import json
import logging
from typing import Dict
from openai import AzureOpenAI
from azure.identity import ClientSecretCredential
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.models import AzureResource, ResourceClassification, WorkloadLevel1

logger = logging.getLogger(__name__)


# Classification instructions for the LLM
CLASSIFICATION_PROMPT = """You are an Azure resource classification expert. Your task is to analyze Azure resources and categorize them into a hierarchical workload taxonomy.

Classification Taxonomy:

Level 1 (Primary Category):
- Infra: Infrastructure and foundational services
- Data: Data storage, processing, and analytics
- Apps: Application hosting and runtime environments

Level 2 (Subcategory) by Level 1:

For "Infra":
- Networking: Virtual networks, load balancers, firewalls, DNS, VPN, ExpressRoute
- Compute: Virtual machines, VM scale sets, availability sets
- Storage: Storage accounts, disks, file shares
- Security: Key vaults, security centers, firewalls
- Management: Resource groups, management groups, policies, blueprints
- Identity: Active Directory, managed identities

For "Data":
- Databases: SQL databases, Cosmos DB, PostgreSQL, MySQL, MariaDB
- Analytics: Synapse, Data Factory, Data Lake, Databricks, Stream Analytics
- Messaging: Event Hubs, Service Bus, Event Grid
- Cache: Redis Cache, CDN
- DataLake: Data Lake Storage, Data Lake Analytics

For "Apps":
- WebApps: App Services, Static Web Apps
- Containers: AKS, Container Instances, Container Apps, Container Registry
- Functions: Azure Functions, Logic Apps
- APIs: API Management, App Configuration
- AI_ML: Cognitive Services, Machine Learning, OpenAI, AI Search

Level 3: The actual Azure service type (e.g., "Virtual Network", "SQL Database", "App Service")

Analyze the following Azure resource and provide classification:

Resource Type: {resource_type}
Resource Name: {resource_name}
Location: {location}
Existing Tags: {existing_tags}

Respond ONLY with valid JSON in this exact format:
{{
  "level_1": "Infra|Data|Apps",
  "level_2": "appropriate subcategory from above",
  "level_3": "specific service name",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of classification",
  "proposed_tags": {{
    "Workload-L1": "value",
    "Workload-L2": "value",
    "Workload-L3": "value",
    "Environment": "inferred from name/tags if possible"
  }}
}}

Ensure confidence is between 0.0 and 1.0 based on how certain you are about the classification."""


class LLMClassifier:
    """Service for classifying Azure resources using Azure AI Foundry."""
    
    def __init__(self):
        """Initialize the LLM classifier with Service Principal authentication."""
        # Use Service Principal authentication
        if settings.auth_mode == "service_principal":
            if not all([settings.azure_client_id, settings.azure_client_secret, settings.azure_tenant_id]):
                raise ValueError(
                    "Service Principal authentication requires AZURE_CLIENT_ID, "
                    "AZURE_CLIENT_SECRET, and AZURE_TENANT_ID environment variables"
                )
            
            logger.info("Initializing LLM client with Service Principal authentication")
            credential = ClientSecretCredential(
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret
            )
            
            # Use Azure AD token provider for authentication
            def token_provider():
                token = credential.get_token("https://cognitiveservices.azure.com/.default")
                return token.token
            
            self.client = AzureOpenAI(
                azure_endpoint=settings.azure_foundry_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=settings.azure_foundry_api_version
            )
        else:
            raise ValueError(f"Unsupported auth_mode: {settings.auth_mode}. Only 'service_principal' is supported.")
        
        self.deployment_name = settings.azure_foundry_deployment_name
        logger.info(f"LLM Classifier initialized with deployment: {self.deployment_name}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def classify_resource(self, resource: AzureResource) -> ResourceClassification:
        """Classify a single Azure resource using LLM.
        
        Args:
            resource: The Azure resource to classify
            
        Returns:
            ResourceClassification object with LLM-generated classification
        """
        try:
            # Prepare the prompt
            prompt = CLASSIFICATION_PROMPT.format(
                resource_type=resource.type,
                resource_name=resource.name,
                location=resource.location,
                existing_tags=json.dumps(resource.tags, indent=2)
            )
            
            logger.info(f"Classifying resource: {resource.name} ({resource.type})")
            
            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an Azure resource classification expert. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent results
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            classification_data = json.loads(response.choices[0].message.content)
            
            # Validate and create classification object
            classification = ResourceClassification(
                resource_id=resource.id,
                resource_name=resource.name,
                resource_type=resource.type,
                level_1=WorkloadLevel1(classification_data["level_1"]),
                level_2=classification_data["level_2"],
                level_3=classification_data["level_3"],
                confidence=float(classification_data["confidence"]),
                reasoning=classification_data["reasoning"],
                proposed_tags=classification_data["proposed_tags"],
                existing_tags=resource.tags
            )
            
            logger.info(
                f"Classified {resource.name}: "
                f"{classification.level_1}/{classification.level_2}/{classification.level_3} "
                f"(confidence: {classification.confidence:.2f})"
            )
            
            return classification
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            raise ValueError(f"Invalid JSON response from LLM: {str(e)}")
        except Exception as e:
            logger.error(f"Error classifying resource {resource.name}: {str(e)}")
            raise
    
    def batch_classify_resources(
        self,
        resources: list[AzureResource],
        max_concurrent: int = 5
    ) -> list[ResourceClassification]:
        """Classify multiple resources.
        
        Args:
            resources: List of Azure resources to classify
            max_concurrent: Maximum number of concurrent classifications
            
        Returns:
            List of ResourceClassification objects
        """
        classifications = []
        errors = []
        
        for i, resource in enumerate(resources):
            try:
                logger.info(f"Classifying resource {i+1}/{len(resources)}: {resource.name}")
                classification = self.classify_resource(resource)
                classifications.append(classification)
            except Exception as e:
                logger.error(f"Error classifying {resource.name}: {str(e)}")
                errors.append({
                    "resource_id": resource.id,
                    "resource_name": resource.name,
                    "error": str(e)
                })
        
        if errors:
            logger.warning(f"Failed to classify {len(errors)} resources")
        
        return classifications
