# Run this script in PowerShell AS ADMINISTRATOR, then reboot.
# Needed for Docker Desktop engine on Windows (WSL2 / Virtual Machine Platform).

$ErrorActionPreference = "Stop"

Write-Host "Enabling Microsoft-Windows-Subsystem-Linux..."
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

Write-Host "Enabling VirtualMachinePlatform..."
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

Write-Host ""
Write-Host "DONE. Reboot Windows, then start Docker Desktop and wait until Engine is running."
Write-Host "After that, from mlops_lab:"
Write-Host '  $env:Path = "C:\Program Files\Docker\Docker\resources\bin;" + $env:Path'
Write-Host "  docker compose build"
Write-Host "  docker tag seeds-api:v1 seeds-api:v2"
Write-Host "  docker compose up -d"
Write-Host "  docker compose ps"
