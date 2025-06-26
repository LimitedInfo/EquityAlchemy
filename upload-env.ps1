param(
    [Parameter(Mandatory=$true)]
    [string]$AppName,
    [string]$EnvFile = ".env"
)

if (-not (Test-Path $EnvFile)) {
    Write-Error "File $EnvFile not found!"
    exit 1
}

Write-Host "Reading environment variables from: $EnvFile" -ForegroundColor Green
Write-Host "Uploading to Fly app: $AppName" -ForegroundColor Green

# Read and parse environment variables
$envVars = @()
$content = Get-Content $EnvFile

foreach ($line in $content) {
    # Skip empty lines and comments
    if ([string]::IsNullOrWhiteSpace($line) -or $line.Trim().StartsWith('#')) {
        continue
    }

    # Only process lines with KEY=VALUE format
    if ($line -match '^[^=]+=') {
        $envVars += $line.Trim()
        $key = $line.Split('=')[0]
        Write-Host "  Found: $key" -ForegroundColor Yellow
    }
}

if ($envVars.Count -eq 0) {
    Write-Warning "No environment variables found in $EnvFile"
    exit 0
}

Write-Host ""
Write-Host "Uploading $($envVars.Count) environment variables..." -ForegroundColor Green

# Upload all at once
flyctl secrets set -a $AppName @envVars

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Success! Uploaded $($envVars.Count) secrets to $AppName" -ForegroundColor Green
} else {
    Write-Error "❌ Failed to upload secrets"
}
