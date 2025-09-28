<#
Run the Onyx development stack using Docker Compose (Windows PowerShell)

What this script does:
- Copies `.vscode/env_template.txt` -> `.vscode/.env` if it doesn't exist
- Ensures `AUTH_TYPE=disabled` is present in `.vscode/.env` (safe for local dev)
- Runs `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d` in
  `deployment/docker_compose` to bring up the full dev stack (exposed ports)
- Waits for http://localhost:3000 to return a successful HTTP status (max 10 minutes)
- Prints helpful logs if the stack fails to become healthy

Usage (from PowerShell):
.
# from repo root (the script is in `scripts`)
# Right-click script -> Run with PowerShell or run in an elevated/regular PowerShell session:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
# .\scripts\run_docker_dev.ps1

Notes:
- Requires Docker Desktop running and accessible to your PowerShell session.
- Edit `.vscode/.env` after the script runs (it will open the file if created) to add any API keys
  (e.g. OPENAI_API_KEY or GEN_AI_API_KEY) if you want LLM features working without UI setup.
- If you prefer to run only a subset of services, edit the `$servicesToStart` variable below.
#>

param(
    [int]$MaxWaitSeconds = 600
)

Set-StrictMode -Version Latest

function Ensure-RepoRoot {
    # Prefer PSScriptRoot which is set to the script's directory when the script is executed
    if ($PSScriptRoot) {
        return (Split-Path -Parent $PSScriptRoot)
    }
    # Fallback to MyInvocation for other invocation styles
    $scriptPath = $MyInvocation.MyCommand.Path
    if (-not $scriptPath) { throw "Unable to determine script path." }
    return (Split-Path -Parent (Split-Path -Parent $scriptPath))
}

$RepoRoot = Ensure-RepoRoot
Write-Host "Repository root: $RepoRoot"

# Ensure .vscode exists and copy env template
$vscodeDir = Join-Path $RepoRoot ".vscode"
$envTemplate = Join-Path $vscodeDir "env_template.txt"
$envFile = Join-Path $vscodeDir ".env"

if (-not (Test-Path $vscodeDir)) {
    New-Item -ItemType Directory -Path $vscodeDir | Out-Null
}

if (-not (Test-Path $envTemplate)) {
    Write-Warning "Env template not found at $envTemplate. Skipping copy. You may need to create .vscode/.env manually."
} else {
    if (-not (Test-Path $envFile)) {
        Copy-Item -Path $envTemplate -Destination $envFile -Force
        Write-Host "Copied env template to .vscode\.env"
        # Open the new .env so user can edit API keys easily
        Write-Host "Opening .vscode\.env for quick edits. Please add OPENAI_API_KEY/GEN_AI_API_KEY if you want LLMs to work without UI setup."
        Start-Process notepad $envFile
    } else {
        Write-Host ".vscode/.env already exists. Leaving it intact."
    }
}

# Ensure AUTH_TYPE=disabled is present for local dev
if (Test-Path $envFile) {
    try {
        $content = Get-Content -Raw -Path $envFile
        if ($content -notmatch '(?m)^\s*AUTH_TYPE\s*=') {
            Add-Content -Path $envFile -Value "`nAUTH_TYPE=disabled"
            Write-Host "Appended AUTH_TYPE=disabled to .vscode/.env"
        } else {
            # replace existing AUTH_TYPE value with disabled for dev convenience
            $updated = ($content -split "`n") | ForEach-Object {
                if ($_ -match '^(\s*AUTH_TYPE\s*=)') { return "$($matches[1])disabled" } else { return $_ }
            }
            $updated -join "`n" | Set-Content -Path $envFile -Encoding UTF8
            Write-Host "Set AUTH_TYPE=disabled in .vscode/.env"
        }
    } catch {
        Write-Warning "Failed to read or update .vscode/.env: $_"
    }
}

# Docker compose directory
$composeDir = Join-Path $RepoRoot "deployment\docker_compose"
if (-not (Test-Path $composeDir)) { throw "Could not find deployment/docker_compose directory at $composeDir" }

# Services to start - adjust if you want fewer services
$servicesToStart = @(
    # core infra
    'index', 'relational_db', 'cache', 'minio',
    # model servers and backend/web (dev override will expose ports)
    'inference_model_server', 'indexing_model_server', 'api_server', 'web_server', 'nginx'
)

# Compose files to use (dev override exposes ports and makes debugging easier)
$composeFiles = @('docker-compose.yml','docker-compose.dev.yml')

# Build up compose -f args as an array to pass to Start-Process
$composeArgsArray = @()
foreach ($f in $composeFiles) {
    $composeArgsArray += '-f'
    $composeArgsArray += $f
}

# Move to compose dir and run docker compose up
Push-Location $composeDir
try {
    Write-Host "Running Docker Compose in: $composeDir"
    $serviceListArg = $servicesToStart
    $cmdArray = $composeArgsArray + @('up','-d') + $serviceListArg
    Write-Host "Executing: docker compose $($cmdArray -join ' ')"
    $proc = Start-Process -FilePath 'docker' -ArgumentList @('compose') + $cmdArray -NoNewWindow -Wait -PassThru -ErrorAction Stop
    Write-Host "Docker compose started (exit code $($proc.ExitCode))."
} catch {
    Write-Error "Failed to run docker compose: $_"
    Pop-Location
    exit 1
}

# Wait for the nginx/nginx-hosted UI at localhost:3000 (HOST_PORT default)
$healthUrl = 'http://localhost:3000'
Write-Host "Waiting for $healthUrl to become ready (max $MaxWaitSeconds seconds)..."

$start = Get-Date
$elapsed = 0
$success = $false
while ($elapsed -lt $MaxWaitSeconds) {
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -in 200,301,302,303,307,308) {
            $success = $true
            break
        }
    } catch {
        # ignore and retry
    }
    Start-Sleep -Seconds 1
    $elapsed = (Get-Date -UFormat %s) - (Get-Date $start -UFormat %s)
}

if ($success) {
    Write-Host "Onyx dev UI is available at $healthUrl"
    Write-Host "Opening browser..."
    Start-Process $healthUrl
    Pop-Location
    exit 0
} else {
    Write-Error "Timed out waiting for $healthUrl after $MaxWaitSeconds seconds."
    Write-Host "Printing docker compose ps and recent logs for key services..."
    try {
        docker compose $composeArgs ps
        docker compose $composeArgs logs --tail 200 api_server
        docker compose $composeArgs logs --tail 200 inference_model_server
        docker compose $composeArgs logs --tail 200 index
        docker compose $composeArgs logs --tail 200 minio
        docker compose $composeArgs logs --tail 200 nginx
    } catch {
        Write-Warning "Failed to fetch docker logs: $_"
    }
    Pop-Location
    exit 2
}
