"""Azure Resource Graph service for discovering resources across subscriptions."""

from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest, QueryRequestOptions
from azure.mgmt.subscription import SubscriptionClient
from typing import List, Dict
import logging

from app.config import settings
from app.models import AzureResource

logger = logging.getLogger(__name__)


class AzureResourceDiscovery:
    """Service for discovering Azure resources using Resource Graph."""
    
    def __init__(self):
        """Initialize the Azure Resource Discovery service."""
        # Use Service Principal authentication if configured
        if settings.auth_mode == "service_principal":
            logger.info("Using Service Principal authentication for Azure Discovery")
            self.credential = ClientSecretCredential(
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret
            )
        else:
            logger.info("Using DefaultAzureCredential for Azure Discovery")
            self.credential = DefaultAzureCredential()
        
        self.resource_graph_client = ResourceGraphClient(self.credential)
        self.subscription_client = SubscriptionClient(self.credential)
    
    def get_all_subscriptions(self) -> List[str]:
        """Get all subscription IDs accessible to the current user.
        
        Returns:
            List of subscription IDs
        """
        try:
            subscriptions = []
            for sub in self.subscription_client.subscriptions.list():
                if sub.state == "Enabled":
                    subscriptions.append(sub.subscription_id)
            
            logger.info(f"Found {len(subscriptions)} enabled subscriptions")
            return subscriptions
        except Exception as e:
            logger.error(f"Error getting subscriptions: {str(e)}")
            # Fallback to configured subscription
            return [settings.azure_subscription_id]
    
    def discover_resources(
        self,
        subscription_ids: List[str] = None,
        resource_groups: List[str] = None,
        resource_types: List[str] = None
    ) -> List[AzureResource]:
        """Discover resources using Azure Resource Graph.
        
        Args:
            subscription_ids: List of subscription IDs to query. If None, uses all accessible.
            resource_groups: Optional filter by resource groups
            resource_types: Optional filter by resource types
            
        Returns:
            List of discovered Azure resources
        """
        if subscription_ids is None:
            subscription_ids = self.get_all_subscriptions()
        
        # Build the query
        query = "Resources"
        
        # Add filters
        where_clauses = []
        
        if resource_groups:
            rg_filter = " or ".join([f"resourceGroup =~ '{rg}'" for rg in resource_groups])
            where_clauses.append(f"({rg_filter})")
        
        if resource_types:
            type_filter = " or ".join([f"type =~ '{rt}'" for rt in resource_types])
            where_clauses.append(f"({type_filter})")
        
        if where_clauses:
            query += f" | where {' and '.join(where_clauses)}"
        
        # Project the fields we need
        query += """
        | project
            id,
            name,
            type,
            resourceGroup,
            subscriptionId,
            location,
            tags,
            properties
        """
        
        logger.info(f"Executing Resource Graph query: {query}")
        logger.info(f"Querying subscriptions: {subscription_ids}")
        
        try:
            # Execute the query
            request = QueryRequest(
                subscriptions=subscription_ids,
                query=query,
                options=QueryRequestOptions(
                    skip_token=None,
                    top=1000  # Max results per page
                )
            )
            
            all_resources = []
            response = self.resource_graph_client.resources(request)
            
            # Process first page
            all_resources.extend(self._process_results(response.data))
            
            # Handle pagination
            while response.skip_token:
                request.options.skip_token = response.skip_token
                response = self.resource_graph_client.resources(request)
                all_resources.extend(self._process_results(response.data))
            
            logger.info(f"Discovered {len(all_resources)} resources")
            return all_resources
            
        except Exception as e:
            logger.error(f"Error discovering resources: {str(e)}")
            raise
    
    def _process_results(self, data: List[Dict]) -> List[AzureResource]:
        """Process Resource Graph results into AzureResource objects.
        
        Args:
            data: Raw data from Resource Graph
            
        Returns:
            List of AzureResource objects
        """
        resources = []
        
        for item in data:
            try:
                resource = AzureResource(
                    id=item.get("id", ""),
                    name=item.get("name", ""),
                    type=item.get("type", ""),
                    resource_group=item.get("resourceGroup", ""),
                    subscription_id=item.get("subscriptionId", ""),
                    location=item.get("location", ""),
                    tags=item.get("tags", {}),
                    properties=item.get("properties", {})
                )
                resources.append(resource)
            except Exception as e:
                logger.warning(f"Error processing resource: {str(e)}")
                continue
        
        return resources
    
    def get_resource_by_id(self, resource_id: str) -> AzureResource:
        """Get a specific resource by its ID.
        
        Args:
            resource_id: The Azure resource ID
            
        Returns:
            AzureResource object
        """
        # Extract subscription ID from resource ID
        # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/{provider}/{type}/{name}
        parts = resource_id.split("/")
        if len(parts) < 3:
            raise ValueError(f"Invalid resource ID: {resource_id}")
        
        subscription_id = parts[2]
        
        query = f"""
        Resources
        | where id =~ '{resource_id}'
        | project
            id,
            name,
            type,
            resourceGroup,
            subscriptionId,
            location,
            tags,
            properties
        """
        
        request = QueryRequest(
            subscriptions=[subscription_id],
            query=query
        )
        
        response = self.resource_graph_client.resources(request)
        
        if not response.data:
            raise ValueError(f"Resource not found: {resource_id}")
        
        return self._process_results(response.data)[0]
