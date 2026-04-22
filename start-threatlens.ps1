param(
    [int]$ApiPort = 5000,
    [int]$DashboardPort = 8501
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $repoRoot "logs"
$apiOutLog = Join-Path $logDir "api.out.log"
$apiErrLog = Join-Path $logDir "api.err.log"
$dashboardOutLog = Join-Path $logDir "dashboard.out.log"
$dashboardErrLog = Join-Path $logDir "dashboard.err.log"
$pidFile = Join-Path $logDir "threatlens.pids.json"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Get-PortProcessId {
    param([int]$Port)

    $match = netstat -ano -p TCP | Select-String ":$Port "
    if (-not $match) {
        return $null
    }

    foreach ($line in $match) {
        $parts = ($line.ToString() -split "\s+") | Where-Object { $_ }
        if ($parts.Length -ge 5 -and $parts[3] -eq "LISTENING") {
            return [int]$parts[4]
        }
    }

    return $null
}

function Start-ServiceProcess {
    param(
        [string]$Name,
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$OutLog,
        [string]$ErrLog,
        [int]$Port
    )

    $existingPid = Get-PortProcessId -Port $Port
    if ($existingPid) {
        Write-Host "$Name already appears to be running on port $Port (PID $existingPid)."
        return @{
            name = $Name
            pid = $existingPid
            port = $Port
            status = "already_running"
        }
    }

    $process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $repoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $OutLog `
        -RedirectStandardError $ErrLog `
        -PassThru

    Start-Sleep -Seconds 2

    if ($process.HasExited) {
        throw "$Name exited during startup. Check $ErrLog and $OutLog."
    }

    Write-Host "$Name started on port $Port (PID $($process.Id))."
    return @{
        name = $Name
        pid = $process.Id
        port = $Port
        status = "started"
    }
}

$results = @()
$results += Start-ServiceProcess `
    -Name "ThreatLens API" `
    -FilePath "python" `
    -ArgumentList @("src\api.py") `
    -OutLog $apiOutLog `
    -ErrLog $apiErrLog `
    -Port $ApiPort

$results += Start-ServiceProcess `
    -Name "ThreatLens Dashboard" `
    -FilePath "python" `
    -ArgumentList @("-m", "streamlit", "run", "dashboard/app.py", "--server.port", "$DashboardPort", "--server.headless", "true", "--browser.gatherUsageStats", "false") `
    -OutLog $dashboardOutLog `
    -ErrLog $dashboardErrLog `
    -Port $DashboardPort

$results | ConvertTo-Json | Set-Content -Path $pidFile

Write-Host ""
Write-Host "ThreatLens startup summary:"
$results | ForEach-Object {
    Write-Host "- $($_.name): $($_.status) (port $($_.port), PID $($_.pid))"
}
Write-Host ""
Write-Host "API: http://127.0.0.1:$ApiPort/health"
Write-Host "Dashboard: http://127.0.0.1:$DashboardPort"
Write-Host "Logs: $logDir"
