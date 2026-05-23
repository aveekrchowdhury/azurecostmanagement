"""Test script to validate Azure Resource Tagger configuration and services."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.services.azure_discovery import AzureResourceDiscovery
from app.services.llm_classifier import LLMClassifier
from app.services.cosmos_db import CosmosDBService
from app.services.tag_manager import AzureTagManager


def test_configuration():
    """Test that all configuration is loaded correctly."""
    print("\n=== Testing Configuration ===")
    print(f"✓ Subscription ID: {settings.azure_subscription_id}")
    print(f"✓ Tenant ID: {settings.azure_tenant_id}")
    print(f"✓ OpenAI Endpoint: {settings.azure_openai_endpoint}")
    print(f"✓ OpenAI Deployment: {settings.azure_openai_deployment_name}")
    print(f"✓ Cosmos DB Endpoint: {settings.cosmos_db_endpoint}")
    print(f"✓ Cosmos DB Database: {settings.cosmos_db_database_name}")
    print(f"✓ Auth Mode: {settings.auth_mode}")
    
    # Check for placeholder values
    warnings = []
    if "YOUR_" in settings.azure_openai_endpoint:
        warnings.append("⚠️  Azure OpenAI endpoint not configured")
    if "YOUR_" in settings.cosmos_db_endpoint:
        warnings.append("⚠️  Cosmos DB endpoint not configured")
    
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  {warning}")
        return False
    
    return True


def test_azure_discovery():
    """Test Azure subscription access."""
    print("\n=== Testing Azure Discovery ===")
    try:
        discovery = AzureResourceDiscovery()
        subscriptions = discovery.get_all_subscriptions()
        print(f"✓ Successfully connected to Azure")
        print(f"✓ Found {len(subscriptions)} accessible subscriptions:")
        for sub_id in subscriptions[:5]:  # Show first 5
            print(f"  - {sub_id}")
        if len(subscriptions) > 5:
            print(f"  ... and {len(subscriptions) - 5} more")
        return True
    except Exception as e:
        print(f"✗ Error accessing Azure: {str(e)}")
        return False


def test_llm_classifier():
    """Test Azure OpenAI connection."""
    print("\n=== Testing LLM Classifier ===")
    try:
        classifier = LLMClassifier()
        
        # Create a test resource
        from app.models import AzureResource
        test_resource = AzureResource(
            id="/subscriptions/test/resourceGroups/test-rg/providers/Microsoft.Network/virtualNetworks/test-vnet",
            name="test-vnet",
            type="Microsoft.Network/virtualNetworks",
            resource_group="test-rg",
            subscription_id="test-sub",
            location="eastus",
            tags={},
            properties={}
        )
        
        print("✓ Testing classification with sample resource...")
        classification = classifier.classify_resource(test_resource)
        print(f"✓ Successfully classified resource")
        print(f"  Level 1: {classification.level_1}")
        print(f"  Level 2: {classification.level_2}")
        print(f"  Level 3: {classification.level_3}")
        print(f"  Confidence: {classification.confidence:.2f}")
        return True
    except Exception as e:
        print(f"✗ Error with LLM classification: {str(e)}")
        print("  Make sure your Azure OpenAI endpoint and API key are configured")
        return False


def test_cosmos_db():
    """Test Cosmos DB connection and operations."""
    print("\n=== Testing Cosmos DB ===")
    try:
        cosmos = CosmosDBService()
        print(f"✓ Successfully connected to Cosmos DB")
        print(f"✓ Database: {settings.cosmos_db_database_name}")
        print(f"✓ Container: {settings.cosmos_db_container_name}")
        
        # Try to get statistics
        stats = cosmos.get_statistics()
        print(f"✓ Statistics query successful")
        print(f"  Total resources: {stats.get('total', 0)}")
        
        return True
    except Exception as e:
        print(f"✗ Error with Cosmos DB: {str(e)}")
        print("  Make sure your Cosmos DB endpoint and key are configured")
        return False


def test_tag_manager():
    """Test Azure Tag Manager initialization."""
    print("\n=== Testing Tag Manager ===")
    try:
        tag_manager = AzureTagManager()
        print(f"✓ Successfully initialized Tag Manager")
        print(f"✓ Ready to apply tags to Azure resources")
        return True
    except Exception as e:
        print(f"✗ Error with Tag Manager: {str(e)}")
        return False


async def run_all_tests():
    """Run all validation tests."""
    print("=" * 60)
    print("Azure Resource Tagger - Configuration & Service Validation")
    print("=" * 60)
    
    results = {
        "Configuration": test_configuration(),
        "Azure Discovery": test_azure_discovery(),
        "LLM Classifier": test_llm_classifier(),
        "Cosmos DB": test_cosmos_db(),
        "Tag Manager": test_tag_manager()
    }
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:20} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed! The backend is ready to use.")
        print("\nNext steps:")
        print("1. Run the backend: python -m uvicorn app.main:app --reload")
        print("2. Visit http://localhost:8000/docs for API documentation")
        print("3. Start the frontend to interact with the API")
    else:
        print("\n⚠️  Some tests failed. Please fix the issues above.")
        print("\nCommon issues:")
        print("- Make sure you're logged in with 'az login'")
        print("- Check that .env file has correct Azure OpenAI credentials")
        print("- Verify Cosmos DB endpoint and key in .env")
    
    return all_passed


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)
