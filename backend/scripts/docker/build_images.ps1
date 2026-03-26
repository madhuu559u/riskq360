param(
  [string]$BackendTag = "medinsight360-backend:latest",
  [string]$FrontendTag = "medinsight360-frontend:latest",
  [string]$FrontendPath = "..\\medinsight360-frontend_codex\\ui-5-react-mantine"
)

$ErrorActionPreference = "Stop"

function Invoke-DockerBuild {
  param(
    [Parameter(Mandatory = $true)][string]$Tag,
    [Parameter(Mandatory = $true)][string]$Dockerfile,
    [Parameter(Mandatory = $true)][string]$Context
  )

  docker build -t $Tag -f $Dockerfile $Context
  if ($LASTEXITCODE -ne 0) {
    throw "[docker] Build failed for tag '$Tag' (docker exit code: $LASTEXITCODE)"
  }
}

Write-Host "[docker] Building backend image: $BackendTag"
Invoke-DockerBuild -Tag $BackendTag -Dockerfile "Dockerfile" -Context "."

if (Test-Path $FrontendPath) {
  $frontendDockerfile = Join-Path $FrontendPath "Dockerfile"
  if (Test-Path $frontendDockerfile) {
    Write-Host "[docker] Building frontend image: $FrontendTag"
    Invoke-DockerBuild -Tag $FrontendTag -Dockerfile $frontendDockerfile -Context $FrontendPath
  } else {
    Write-Host "[docker] Frontend Dockerfile not found at $frontendDockerfile. Skipping frontend build."
  }
} else {
  Write-Host "[docker] Frontend path not found: $FrontendPath. Skipping frontend build."
}

Write-Host "[docker] Build complete."
