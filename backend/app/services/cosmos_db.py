"""Cosmos DB service for storing and managing resource classifications."""

import logging
from datetime import datetime
from typing import List, Optional, Dict
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import ClientSecretCredential

from app.config import settings
from app.models import (
    ResourceClassification,
    StoredClassification,
    ClassificationStatus,
    AzureResource
)

logger = logging.getLogger(__name__)


class CosmosDBService:
    """Service for managing classifications in Cosmos DB."""
    
    def __init__(self):
        """Initialize Cosmos DB client and ensure database/container exist."""
        # Use Service Principal authentication
        credential = ClientSecretCredential(
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret
        )
        
        self.client = CosmosClient(
            settings.cosmos_db_endpoint,
            credential=credential
        )
        self.database_name = settings.cosmos_db_database_name
        self.container_name = settings.cosmos_db_container_name
        self._initialized = False
        self.partition_key_path = None
        
    def _ensure_initialized(self):
        """Lazy initialization of database and container."""
        if not self._initialized:
            self._ensure_database_exists()
            self._ensure_container_exists()
            self._initialized = True
    
    def _ensure_database_exists(self):
        """Create database if it doesn't exist."""
        try:
            self.database = self.client.get_database_client(self.database_name)
            # Try to read database properties to verify it exists
            self.database.read()
            logger.info(f"Connected to existing database: {self.database_name}")
        except CosmosResourceNotFoundError:
            logger.info(f"Creating database: {self.database_name}")
            self.database = self.client.create_database(self.database_name)
    
    def _ensure_container_exists(self):
        """Create container if it doesn't exist."""
        try:
            self.container = self.database.get_container_client(self.container_name)
            # Try to read container properties to verify it exists
            props = self.container.read()
            self.partition_key_path = self._extract_partition_key_path(props)
            logger.info(f"Connected to existing container: {self.container_name}")
        except CosmosResourceNotFoundError:
            logger.info(f"Creating container: {self.container_name}")
            self.container = self.database.create_container(
                id=self.container_name,
                partition_key=PartitionKey(path="/subscription_id"),
                offer_throughput=400  # Minimum RU/s
            )
            props = self.container.read()
            self.partition_key_path = self._extract_partition_key_path(props)

    def _extract_partition_key_path(self, container_properties: Dict) -> str:
        """Extract the configured partition key path from container metadata."""
        paths = container_properties.get("partitionKey", {}).get("paths", [])
        if paths:
            return paths[0]
        return "/subscription_id"

    def _get_partition_key_value(self, normalized_id: str, subscription_id: str) -> str:
        """Resolve partition key value for read operations based on live container config."""
        if self.partition_key_path in ("/id",):
            return normalized_id

        if self.partition_key_path in ("/subscription_id", "/subscriptionId", "/partition_key", "/partitionKey"):
            return subscription_id

        logger.warning(
            "Unknown partition key path '%s'. Falling back to subscription_id.",
            self.partition_key_path,
        )
        return subscription_id
    
    def save_classification(
        self,
        classification: ResourceClassification,
        resource: AzureResource
    ) -> StoredClassification:
        """Save a resource classification to Cosmos DB.
        
        Args:
            classification: The classification to save
            resource: The original Azure resource
            
        Returns:
            StoredClassification object
        """
        self._ensure_initialized()
        stored = StoredClassification(
            id=self._normalize_id(resource.id),
            partition_key=resource.subscription_id,
            resource_id=resource.id,
            resource_name=resource.name,
            resource_type=resource.type,
            resource_group=resource.resource_group,
            subscription_id=resource.subscription_id,
            location=resource.location,
            level_1=classification.level_1.value,
            level_2=classification.level_2,
            level_3=classification.level_3,
            confidence=classification.confidence,
            reasoning=classification.reasoning,
            proposed_tags=classification.proposed_tags,
            existing_tags=classification.existing_tags,
            status=ClassificationStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        try:
            # Upsert the document - use mode='json' to properly serialize datetime objects
            self.container.upsert_item(stored.model_dump(mode='json'))
            logger.info(f"Saved classification for: {resource.name}")
            return stored
        except Exception as e:
            logger.error(f"Error saving classification: {str(e)}")
            raise
    
    def get_classification(self, resource_id: str, subscription_id: str) -> Optional[StoredClassification]:
        """Get a classification by resource ID.
        
        Args:
            resource_id: The Azure resource ID
            subscription_id: The subscription ID (partition key)
            
        Returns:
            StoredClassification or None if not found
        """
        self._ensure_initialized()
        normalized_id = self._normalize_id(resource_id)
        partition_key_value = self._get_partition_key_value(normalized_id, subscription_id)

        try:
            item = self.container.read_item(
                item=normalized_id,
                partition_key=partition_key_value
            )
            return StoredClassification(**item)
        except CosmosResourceNotFoundError:
            # Fall back to a query for compatibility with legacy containers/data
            # where partition key strategy may have changed over time.
            query = "SELECT TOP 1 * FROM c WHERE c.resource_id = @resource_id AND c.subscription_id = @subscription_id"
            parameters = [
                {"name": "@resource_id", "value": resource_id},
                {"name": "@subscription_id", "value": subscription_id},
            ]
            items = list(
                self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True,
                )
            )
            if not items:
                return None
            return StoredClassification(**items[0])
        except Exception as e:
            logger.error(f"Error getting classification: {str(e)}")
            raise
    
    def get_all_classifications(
        self,
        subscription_id: Optional[str] = None,
        status: Optional[ClassificationStatus] = None,
        min_confidence: Optional[float] = None,
        max_confidence: Optional[float] = None,
        level1: Optional[str] = None,
        level2: Optional[str] = None,
        level3: Optional[str] = None,
        limit: int = 1000
    ) -> List[StoredClassification]:
        """Get all classifications with optional filters.
        
        Args:
            subscription_id: Optional subscription filter
            status: Optional status filter
            min_confidence: Minimum confidence threshold (0.0-1.0)
            max_confidence: Maximum confidence threshold (0.0-1.0)
            level1: Filter by level1 taxonomy
            level2: Filter by level2 taxonomy
            level3: Filter by level3 taxonomy
            limit: Maximum number of results
            
        Returns:
            List of StoredClassification objects
        """
        self._ensure_initialized()
        query = "SELECT * FROM c"
        parameters = []
        where_clauses = []
        
        if subscription_id:
            where_clauses.append("c.subscription_id = @subscription_id")
            parameters.append({"name": "@subscription_id", "value": subscription_id})
        
        if status:
            where_clauses.append("c.status = @status")
            parameters.append({"name": "@status", "value": status.value})
        
        if min_confidence is not None:
            where_clauses.append("c.confidence >= @min_confidence")
            parameters.append({"name": "@min_confidence", "value": min_confidence})
        
        if max_confidence is not None:
            where_clauses.append("c.confidence <= @max_confidence")
            parameters.append({"name": "@max_confidence", "value": max_confidence})
        
        if level1:
            where_clauses.append("c.level_1 = @level1")
            parameters.append({"name": "@level1", "value": level1})
        
        if level2:
            where_clauses.append("c.level_2 = @level2")
            parameters.append({"name": "@level2", "value": level2})
        
        if level3:
            where_clauses.append("c.level_3 = @level3")
            parameters.append({"name": "@level3", "value": level3})
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY c.created_at DESC"
        query += f" OFFSET 0 LIMIT {limit}"
        
        try:
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            return [StoredClassification(**item) for item in items]
        except Exception as e:
            logger.error(f"Error querying classifications: {str(e)}")
            raise
    
    def update_classification(
        self,
        resource_id: str,
        subscription_id: str,
        updates: Dict
    ) -> StoredClassification:
        """Update a classification.
        
        Args:
            resource_id: The Azure resource ID
            subscription_id: The subscription ID (partition key)
            updates: Dictionary of fields to update
            
        Returns:
            Updated StoredClassification
        """
        classification = self.get_classification(resource_id, subscription_id)
        if not classification:
            raise ValueError(f"Classification not found: {resource_id}")
        
        # Update fields
        for key, value in updates.items():
            if hasattr(classification, key) and value is not None:
                setattr(classification, key, value)
        
        classification.updated_at = datetime.utcnow()
        
        try:
            self.container.upsert_item(classification.model_dump(mode='json'))
            logger.info(f"Updated classification for: {resource_id}")
            return classification
        except Exception as e:
            logger.error(f"Error updating classification: {str(e)}")
            raise
    
    def approve_classification(
        self,
        resource_id: str,
        subscription_id: str
    ) -> StoredClassification:
        """Approve a classification.
        
        Args:
            resource_id: The Azure resource ID
            subscription_id: The subscription ID (partition key)
            
        Returns:
            Updated StoredClassification
        """
        return self.update_classification(
            resource_id,
            subscription_id,
            {"status": ClassificationStatus.APPROVED}
        )
    
    def reject_classification(
        self,
        resource_id: str,
        subscription_id: str
    ) -> StoredClassification:
        """Reject a classification.
        
        Args:
            resource_id: The Azure resource ID
            subscription_id: The subscription ID (partition key)
            
        Returns:
            Updated StoredClassification
        """
        return self.update_classification(
            resource_id,
            subscription_id,
            {"status": ClassificationStatus.REJECTED}
        )
    
    def mark_applied(
        self,
        resource_id: str,
        subscription_id: str,
        error_message: Optional[str] = None
    ) -> StoredClassification:
        """Mark a classification as applied (or failed).
        
        Args:
            resource_id: The Azure resource ID
            subscription_id: The subscription ID (partition key)
            error_message: Optional error message if application failed
            
        Returns:
            Updated StoredClassification
        """
        updates = {
            "status": ClassificationStatus.FAILED if error_message else ClassificationStatus.APPLIED,
            "applied_at": datetime.utcnow()
        }
        
        if error_message:
            updates["error_message"] = error_message
        
        return self.update_classification(resource_id, subscription_id, updates)
    
    def _normalize_id(self, resource_id: str) -> str:
        """Normalize a resource ID to be a valid Cosmos DB document ID.
        
        Cosmos DB document IDs can't contain: / \ ? #
        We'll use base64 encoding or simple replacement.
        
        Args:
            resource_id: The Azure resource ID
            
        Returns:
            Normalized ID safe for Cosmos DB
        """
        import base64
        # Use URL-safe base64 encoding
        return base64.urlsafe_b64encode(resource_id.encode()).decode()
    
    def get_statistics(self, subscription_id: Optional[str] = None) -> Dict:
        """Get classification statistics.
        
        Args:
            subscription_id: Optional subscription filter
            
        Returns:
            Dictionary with statistics
        """
        self._ensure_initialized()
        
        # Get all items and compute statistics in Python
        # Cosmos DB doesn't support CASE inside aggregate functions well
        query = "SELECT * FROM c"
        parameters = []
        if subscription_id:
            query += " WHERE c.subscription_id = @subscription_id"
            parameters.append({"name": "@subscription_id", "value": subscription_id})
        
        try:
            results = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            # Compute statistics in Python
            stats = {
                "total": len(results),
                "pending": sum(1 for r in results if r.get("status") == "pending"),
                "approved": sum(1 for r in results if r.get("status") == "approved"),
                "rejected": sum(1 for r in results if r.get("status") == "rejected"),
                "applied": sum(1 for r in results if r.get("status") == "applied"),
                "failed": sum(1 for r in results if r.get("status") == "failed")
            }
            
            return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {str(e)}")
            raise
