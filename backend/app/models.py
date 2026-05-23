"""Data models for the Azure Resource Tagger application."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime


def to_camel(string: str) -> str:
    """Convert snake_case to camelCase."""
    components = string.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


class WorkloadLevel1(str, Enum):
    """Top-level workload categories."""
    INFRA = "Infra"
    DATA = "Data"
    APPS = "Apps"


class WorkloadLevel2Infra(str, Enum):
    """Level 2 categories for Infrastructure."""
    NETWORKING = "Networking"
    COMPUTE = "Compute"
    STORAGE = "Storage"
    SECURITY = "Security"
    MANAGEMENT = "Management"
    IDENTITY = "Identity"


class WorkloadLevel2Data(str, Enum):
    """Level 2 categories for Data."""
    DATABASES = "Databases"
    ANALYTICS = "Analytics"
    MESSAGING = "Messaging"
    CACHE = "Cache"
    DATA_LAKE = "DataLake"


class WorkloadLevel2Apps(str, Enum):
    """Level 2 categories for Apps."""
    WEB_APPS = "WebApps"
    CONTAINERS = "Containers"
    FUNCTIONS = "Functions"
    APIS = "APIs"
    AI_ML = "AI_ML"


class AzureResource(BaseModel):
    """Represents an Azure resource."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    
    id: str
    name: str
    type: str
    resource_group: str
    subscription_id: str
    location: str
    tags: Dict[str, str] = Field(default_factory=dict)
    properties: Dict = Field(default_factory=dict)


class ResourceClassification(BaseModel):
    """LLM-generated classification for a resource."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    
    resource_id: str
    resource_name: str
    resource_type: str
    level_1: WorkloadLevel1
    level_2: str
    level_3: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    proposed_tags: Dict[str, str]
    existing_tags: Dict[str, str] = Field(default_factory=dict)
    

class ClassificationStatus(str, Enum):
    """Status of a resource classification."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    FAILED = "failed"


class StoredClassification(BaseModel):
    """Classification stored in Cosmos DB with status tracking."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True
    )
    
    id: str  # Cosmos DB document ID (resource ID)
    partition_key: str  # Subscription ID for partitioning
    resource_id: str
    resource_name: str
    resource_type: str
    resource_group: str
    subscription_id: str
    location: str
    level_1: str
    level_2: str
    level_3: str
    confidence: float
    reasoning: str
    proposed_tags: Dict[str, str]
    existing_tags: Dict[str, str]
    status: ClassificationStatus = ClassificationStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    applied_at: Optional[datetime] = None
    error_message: Optional[str] = None


class BatchApprovalRequest(BaseModel):
    """Request to approve/reject multiple classifications."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    resource_ids: List[str]
    approved: bool = True
    apply_immediately: bool = False


class BatchRejectRequest(BaseModel):
    """Request to reject multiple classifications."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    resource_ids: List[str]


class BatchApplyTagsRequest(BaseModel):
    """Request to apply tags to specific resources."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    resource_ids: List[str]


class UpdateClassificationRequest(BaseModel):
    """Request to update a classification."""
    level_1: Optional[str] = None
    level_2: Optional[str] = None
    level_3: Optional[str] = None
    proposed_tags: Optional[Dict[str, str]] = None


class DiscoveryRequest(BaseModel):
    """Request to discover and classify resources."""
    subscription_ids: Optional[List[str]] = None
    resource_groups: Optional[List[str]] = None
    resource_types: Optional[List[str]] = None
    force_refresh: bool = False


class DiscoveryResponse(BaseModel):
    """Response from resource discovery."""
    total_discovered: int
    total_classified: int
    total_errors: int
    message: str
