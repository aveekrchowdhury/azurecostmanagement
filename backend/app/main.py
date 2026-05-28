"""Main FastAPI application for Azure Resource Tagger."""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional

from app.config import settings
from app.models import (
    DiscoveryRequest,
    DiscoveryResponse,
    StoredClassification,
    BatchApprovalRequest,
    BatchRejectRequest,
    BatchApplyTagsRequest,
    UpdateClassificationRequest,
    ClassificationStatus
)
from app.services.azure_discovery import AzureResourceDiscovery
from app.services.llm_classifier import LLMClassifier
from app.services.cosmos_db import CosmosDBService
from app.services.tag_manager import AzureTagManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app with camelCase response serialization
app = FastAPI(
    title="Azure Resource Tagger",
    description="Automatically discover, classify, and tag Azure resources using LLM",
    version="1.0.0",
)

# Configure CORS
allowed_origins = {
    settings.frontend_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
discovery_service = AzureResourceDiscovery()
classifier_service = LLMClassifier()
cosmos_service = CosmosDBService()
tag_manager = AzureTagManager()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Azure Resource Tagger",
        "version": "1.0.0"
    }


@app.get("/api/subscriptions")
async def get_subscriptions():
    """Get all accessible Azure subscriptions."""
    try:
        subscriptions = discovery_service.get_all_subscriptions()
        return {
            "subscriptions": subscriptions,
            "count": len(subscriptions)
        }
    except Exception as e:
        logger.error(f"Error getting subscriptions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resources/discover", response_model=DiscoveryResponse)
async def discover_and_classify_resources(request: DiscoveryRequest):
    """Discover Azure resources and classify them using LLM.
    
    This endpoint:
    1. Discovers resources using Azure Resource Graph
    2. Classifies each resource using Azure OpenAI
    3. Stores classifications in Cosmos DB
    """
    try:
        logger.info("Starting resource discovery and classification")
        
        # Discover resources
        resources = discovery_service.discover_resources(
            subscription_ids=request.subscription_ids,
            resource_groups=request.resource_groups,
            resource_types=request.resource_types
        )
        
        if not resources:
            return DiscoveryResponse(
                total_discovered=0,
                total_classified=0,
                total_errors=0,
                message="No resources found matching the criteria"
            )
        
        logger.info(f"Discovered {len(resources)} resources")
        
        # Classify resources
        classifications = []
        errors = 0
        
        for i, resource in enumerate(resources):
            try:
                # Check if already classified and not forcing refresh
                if not request.force_refresh:
                    existing = cosmos_service.get_classification(
                        resource.id,
                        resource.subscription_id
                    )
                    if existing:
                        logger.info(f"Skipping already classified resource: {resource.name}")
                        classifications.append(existing)
                        continue
                
                # Classify the resource
                logger.info(f"Classifying {i+1}/{len(resources)}: {resource.name}")
                classification = classifier_service.classify_resource(resource)
                
                # Store in Cosmos DB
                stored = cosmos_service.save_classification(classification, resource)
                classifications.append(stored)
                
            except Exception as e:
                logger.error(f"Error processing {resource.name}: {str(e)}")
                errors += 1
        
        return DiscoveryResponse(
            total_discovered=len(resources),
            total_classified=len(classifications),
            total_errors=errors,
            message=f"Discovered {len(resources)} resources, classified {len(classifications)}"
        )
        
    except Exception as e:
        logger.error(f"Error in discovery process: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/resources", response_model=List[StoredClassification], response_model_by_alias=True)
async def get_classifications(
    subscription_id: Optional[str] = None,
    status: Optional[ClassificationStatus] = None,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
    level1: Optional[str] = None,
    level2: Optional[str] = None,
    level3: Optional[str] = None,
    limit: int = 1000
):
    """Get all resource classifications with optional filters."""
    try:
        classifications = cosmos_service.get_all_classifications(
            subscription_id=subscription_id,
            status=status,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
            level1=level1,
            level2=level2,
            level3=level3,
            limit=limit
        )
        return classifications
    except Exception as e:
        logger.error(f"Error getting classifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/resources/{resource_id:path}", response_model=StoredClassification, response_model_by_alias=True)
async def get_classification(resource_id: str, subscription_id: str):
    """Get a specific resource classification."""
    try:
        classification = cosmos_service.get_classification(resource_id, subscription_id)
        if not classification:
            raise HTTPException(status_code=404, detail="Classification not found")
        return classification
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting classification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/resources/{resource_id:path}")
async def update_classification(
    resource_id: str,
    subscription_id: str,
    request: UpdateClassificationRequest
):
    """Update a resource classification."""
    try:
        updates = request.model_dump(exclude_none=True)
        classification = cosmos_service.update_classification(
            resource_id,
            subscription_id,
            updates
        )
        return classification
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating classification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resources/approve")
async def batch_approve(request: BatchApprovalRequest):
    """Approve or reject multiple classifications and optionally apply tags immediately."""
    try:
        results = []
        
        for resource_id in request.resource_ids:
            # Extract subscription_id from resource_id
            # Format: /subscriptions/{sub}/...
            parts = resource_id.split("/")
            if len(parts) < 3:
                results.append({
                    "resource_id": resource_id,
                    "success": False,
                    "error": "Invalid resource ID format"
                })
                continue
            
            subscription_id = parts[2]
            
            try:
                # Approve or reject the classification based on the approved field
                if request.approved:
                    classification = cosmos_service.approve_classification(
                        resource_id,
                        subscription_id
                    )
                    status = "approved"
                else:
                    classification = cosmos_service.reject_classification(
                        resource_id,
                        subscription_id
                    )
                    status = "rejected"
                
                result = {
                    "resource_id": resource_id,
                    "success": True,
                    "status": status
                }
                
                # Apply tags immediately if requested (only for approved)
                if request.approved and request.apply_immediately:
                    try:
                        tag_manager.apply_tags(
                            resource_id,
                            classification.proposed_tags,
                            merge=True
                        )
                        cosmos_service.mark_applied(resource_id, subscription_id)
                        result["status"] = "applied"
                    except Exception as e:
                        logger.error(f"Error applying tags: {str(e)}")
                        cosmos_service.mark_applied(
                            resource_id,
                            subscription_id,
                            error_message=str(e)
                        )
                        result["success"] = False
                        result["error"] = f"Approved but failed to apply: {str(e)}"
                
                results.append(result)
                
            except Exception as e:
                results.append({
                    "resource_id": resource_id,
                    "success": False,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "total": len(request.resource_ids),
            "successful": success_count,
            "failed": len(request.resource_ids) - success_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch approval: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resources/reject")
async def batch_reject(request: BatchRejectRequest):
    """Reject multiple classifications."""
    try:
        results = []
        
        for resource_id in request.resource_ids:
            parts = resource_id.split("/")
            if len(parts) < 3:
                results.append({
                    "resource_id": resource_id,
                    "success": False,
                    "error": "Invalid resource ID format"
                })
                continue
            
            subscription_id = parts[2]
            
            try:
                cosmos_service.reject_classification(resource_id, subscription_id)
                results.append({
                    "resource_id": resource_id,
                    "success": True
                })
            except Exception as e:
                results.append({
                    "resource_id": resource_id,
                    "success": False,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "total": len(request.resource_ids),
            "successful": success_count,
            "failed": len(request.resource_ids) - success_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error in batch rejection: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/resources/apply")
async def apply_approved_tags(request: BatchApplyTagsRequest = None):
    """Apply tags for approved classifications. If resource_ids provided, apply only those; otherwise apply all approved."""
    try:
        # If specific resources provided, apply only those (must be approved)
        if request and request.resource_ids:
            classifications = []
            logger.info(f"Applying tags for {len(request.resource_ids)} resource(s)")
            for resource_id in request.resource_ids:
                logger.info(f"Processing resource_id: {resource_id}")
                parts = resource_id.split("/")
                if len(parts) < 3:
                    logger.warning(f"Invalid resource_id format: {resource_id}")
                    continue
                subscription_id = parts[2]
                logger.info(f"Extracted subscription_id: {subscription_id}")
                
                # Get the classification
                classification = cosmos_service.get_classification(resource_id, subscription_id)
                logger.info(f"Classification found: {classification is not None}")
                if classification:
                    logger.info(f"Classification status: {classification.status}")
                    # Only include approved classifications
                    if classification.status == ClassificationStatus.APPROVED:
                        classifications.append(classification)
                    else:
                        logger.warning(f"Skipping resource {resource_id} - status is {classification.status}, not APPROVED")
        else:
            # Get all approved classifications
            classifications = cosmos_service.get_all_classifications(
                status=ClassificationStatus.APPROVED
            )
        
        if not classifications:
            return {
                "message": "No classifications to apply",
                "total": 0,
                "successful": 0,
                "failed": 0,
                "results": []
            }
        
        logger.info(f"Applying tags to {len(classifications)} resources")
        
        # Prepare batch
        resources_and_tags = [
            (c.resource_id, c.proposed_tags)
            for c in classifications
        ]
        
        # Apply tags
        results = tag_manager.batch_apply_tags(resources_and_tags, merge=True)
        
        # Update statuses in Cosmos DB
        for result in results:
            resource_id = result["resource_id"]
            # Extract subscription ID
            subscription_id = resource_id.split("/")[2]
            
            if result["success"]:
                cosmos_service.mark_applied(resource_id, subscription_id)
            else:
                cosmos_service.mark_applied(
                    resource_id,
                    subscription_id,
                    error_message=result["error"]
                )
        
        success_count = sum(1 for r in results if r["success"])
        
        return {
            "message": f"Applied tags to {success_count}/{len(results)} resources",
            "total": len(results),
            "successful": success_count,
            "failed": len(results) - success_count,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error applying tags: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/statistics")
async def get_statistics(subscription_id: Optional[str] = None):
    """Get classification statistics."""
    try:
        stats = cosmos_service.get_statistics(subscription_id)
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True
    )
