# Assign RBAC roles to Service Principal across multiple subscriptions
# Useful when you need to manage resources across multiple Azure subscriptions

param(
    [Parameter(Mandatory=$true)]
    [string]$ClientId,
    
    [Parameter(Mandatory=$false)]
    [string[]]$SubscriptionIds = @()  # Empty = all accessible subscriptions
)

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Multi-Subscription RBAC Assignment" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Service Principal Client ID: $ClientId`n" -ForegroundColor Cyan

# Get all subscriptions if not specified
if ($SubscriptionIds.Count -eq 0) {
    Write-Host "Getting all accessible subscriptions..." -ForegroundColor Cyan
    $SubscriptionIds = az account list --query "[].id" -o tsv
    
    if ($null -eq $SubscriptionIds -or $SubscriptionIds.Count -eq 0) {
        Write-Host "No subscriptions found!" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Found $($SubscriptionIds.Count) subscription(s)`n" -ForegroundColor Green
} else {
    Write-Host "Processing $($SubscriptionIds.Count) specified subscription(s)`n" -ForegroundColor Green
}

# Track results
$successCount = 0
$failureCount = 0
$results = @()

# Assign roles to each subscription
foreach ($subId in $SubscriptionIds) {
    Write-Host "Processing subscription: $subId" -ForegroundColor Cyan
    
    try {
        # Set subscription context
        az account set --subscription $subId --output none
        
        # Get subscription name
        $subName = az account show --query name -o tsv
        Write-Host "  Name: $subName" -ForegroundColor White
        
        # Reader role
        Write-Host "  [1/2] Assigning Reader role..." -ForegroundColor Gray
        $readerResult = az role assignment create `
          --role "Reader" `
          --assignee $ClientId `
          --scope "/subscriptions/$subId" `
          --output none 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Reader role assigned" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Reader role may already exist" -ForegroundColor Yellow
        }
        
        # Tag Contributor role
        Write-Host "  [2/2] Assigning Tag Contributor role..." -ForegroundColor Gray
        $tagResult = az role assignment create `
          --role "Tag Contributor" `
          --assignee $ClientId `
          --scope "/subscriptions/$subId" `
          --output none 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Tag Contributor role assigned" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Tag Contributor role may already exist" -ForegroundColor Yellow
        }
        
        $successCount++
        $results += [PSCustomObject]@{
            SubscriptionId = $subId
            SubscriptionName = $subName
            Status = "Success"
        }
        
        Write-Host "  ✓ Completed for subscription: $subName`n" -ForegroundColor Green
        
    } catch {
        Write-Host "  ✗ Failed for subscription: $subId" -ForegroundColor Red
        Write-Host "  Error: $_`n" -ForegroundColor Red
        $failureCount++
        
        $results += [PSCustomObject]@{
            SubscriptionId = $subId
            SubscriptionName = "Error"
            Status = "Failed"
        }
    }
}

# Display summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Summary" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Total subscriptions: $($SubscriptionIds.Count)"
Write-Host "Successful: $successCount" -ForegroundColor Green
Write-Host "Failed: $failureCount" -ForegroundColor $(if ($failureCount -gt 0) { "Red" } else { "Green" })
Write-Host ""

# Display results table
Write-Host "Results:" -ForegroundColor Cyan
$results | Format-Table -AutoSize

if ($failureCount -eq 0) {
    Write-Host "✅ All subscriptions configured successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some subscriptions failed. Review errors above." -ForegroundColor Yellow
}

Write-Host ""
