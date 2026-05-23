"""Service for applying tags to Azure resources."""

import logging
from typing import Dict, List
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient

from app.config import settings

logger = logging.getLogger(__name__)


class AzureTagManager:
    """Service for applying tags to Azure resources."""
    
    def __init__(self):
        """Initialize the Azure Tag Manager."""
        # Use Service Principal authentication if configured
        if settings.auth_mode == "service_principal":
            logger.info("Using Service Principal authentication for Azure Tag Manager")
            self.credential = ClientSecretCredential(
                tenant_id=settings.azure_tenant_id,
                client_id=settings.azure_client_id,
                client_secret=settings.azure_client_secret
            )
        else:
            logger.info("Using DefaultAzureCredential for Azure Tag Manager")
            self.credential = DefaultAzureCredential()
        
        self._resource_clients = {}  # Cache clients per subscription
    
    def _get_resource_client(self, subscription_id: str) -> ResourceManagementClient:
        """Get or create a Resource Management client for a subscription.
        
        Args:
            subscription_id: The subscription ID
            
        Returns:
            ResourceManagementClient for the subscription
        """
        if subscription_id not in self._resource_clients:
            self._resource_clients[subscription_id] = ResourceManagementClient(
                self.credential,
                subscription_id
            )
        return self._resource_clients[subscription_id]
    
    def apply_tags(
        self,
        resource_id: str,
        tags: Dict[str, str],
        merge: bool = True
    ) -> Dict[str, str]:
        """Apply tags to an Azure resource.
        
        Args:
            resource_id: The full Azure resource ID
            tags: Dictionary of tags to apply
            merge: If True, merge with existing tags. If False, replace all tags.
            
        Returns:
            Dictionary of final tags on the resource
            
        Raises:
            ValueError: If resource_id is invalid
            ResourceNotFoundError: If resource doesn't exist
        """
        try:
            # Parse the resource ID
            # Format: /subscriptions/{sub}/resourceGroups/{rg}/providers/{provider}/{type}/{name}
            parts = resource_id.split("/")
            if len(parts) < 9 or parts[1] != "subscriptions" or parts[3] != "resourceGroups":
                raise ValueError(f"Invalid resource ID format: {resource_id}")
            
            subscription_id = parts[2]
            logger.info(f"Applying tags to: {resource_id}")
            logger.info(f"Tags: {tags}")
            
            client = self._get_resource_client(subscription_id)

            operation = "Merge" if merge else "Replace"
            poller = client.tags.begin_update_at_scope(
                scope=resource_id,
                parameters={
                    "operation": operation,
                    "properties": {
                        "tags": tags,
                    },
                },
            )
            updated_tags_resource = poller.result()

            # Ensure we always return the final tag set from Azure.
            final_tags = {}
            if updated_tags_resource and getattr(updated_tags_resource, "properties", None):
                final_tags = updated_tags_resource.properties.tags or {}

            if not final_tags:
                current = client.tags.get_at_scope(resource_id)
                if current and getattr(current, "properties", None):
                    final_tags = current.properties.tags or {}
            
            logger.info(f"Successfully applied tags to: {resource_id}")
            return final_tags
        except Exception as e:
            logger.error(f"Error applying tags to {resource_id}: {str(e)}")
            raise
    
    def batch_apply_tags(
        self,
        resources_and_tags: List[tuple[str, Dict[str, str]]],
        merge: bool = True
    ) -> List[Dict]:
        """Apply tags to multiple resources.
        
        Args:
            resources_and_tags: List of (resource_id, tags) tuples
            merge: If True, merge with existing tags
            
        Returns:
            List of dictionaries with results:
            [{"resource_id": str, "success": bool, "tags": dict, "error": str}]
        """
        results = []
        
        for resource_id, tags in resources_and_tags:
            try:
                final_tags = self.apply_tags(resource_id, tags, merge=merge)
                results.append({
                    "resource_id": resource_id,
                    "success": True,
                    "tags": final_tags,
                    "error": None
                })
            except Exception as e:
                logger.error(f"Failed to apply tags to {resource_id}: {str(e)}")
                results.append({
                    "resource_id": resource_id,
                    "success": False,
                    "tags": {},
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        logger.info(
            f"Batch tag application complete: "
            f"{success_count}/{len(results)} successful"
        )
        
        return results
    
    def remove_tags(
        self,
        resource_id: str,
        tag_keys: List[str]
    ) -> Dict[str, str]:
        """Remove specific tags from a resource.
        
        Args:
            resource_id: The full Azure resource ID
            tag_keys: List of tag keys to remove
            
        Returns:
            Dictionary of remaining tags on the resource
        """
        try:
            parts = resource_id.split("/")
            if len(parts) < 9:
                raise ValueError(f"Invalid resource ID format: {resource_id}")
            
            subscription_id = parts[2]
            client = self._get_resource_client(subscription_id)

            tags_to_delete = {key: "" for key in tag_keys}
            poller = client.tags.begin_update_at_scope(
                scope=resource_id,
                parameters={
                    "operation": "Delete",
                    "properties": {
                        "tags": tags_to_delete,
                    },
                },
            )
            poller.result()

            current = client.tags.get_at_scope(resource_id)
            remaining_tags = {}
            if current and getattr(current, "properties", None):
                remaining_tags = current.properties.tags or {}
            
            logger.info(f"Removed tags {tag_keys} from: {resource_id}")
            return remaining_tags
            
        except Exception as e:
            logger.error(f"Error removing tags from {resource_id}: {str(e)}")
            raise
