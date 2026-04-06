param(
    [string]$ExePath,
    [int]$Runs = 5,
    [int]$WindowTimeoutMs = 15000,
    [int]$IdleTimeoutMs = 10000,
    [int]$CooldownSeconds = 3,
    [string]$CsvPath = ""
)

if (-not $ExePath) {
    $candidatePaths = @(
        "$Env:ProgramFiles\Home Unit Calculator\HomeUnitCalculator.exe",
        "$Env:ProgramFiles(x86)\Home Unit Calculator\HomeUnitCalculator.exe",
        "dist\HomeUnitCalculator\HomeUnitCalculator.exe"
    )

    foreach ($candidate in $candidatePaths) {
        if (Test-Path $candidate) {
            $ExePath = $candidate
            break
        }
    }
}

if (-not $ExePath -or -not (Test-Path $ExePath)) {
    throw "Executable not found. Pass -ExePath or install/build the app first."
}

$results = @()

for ($run = 1; $run -le $Runs; $run++) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $process = Start-Process -FilePath $ExePath -PassThru

    $windowMs = $null
    $windowDeadline = [System.Diagnostics.Stopwatch]::StartNew()

    while (-not $process.HasExited -and $windowDeadline.ElapsedMilliseconds -lt $WindowTimeoutMs) {
        Start-Sleep -Milliseconds 50
        $process.Refresh()
        if ($process.MainWindowHandle -ne 0) {
            $windowMs = $sw.ElapsedMilliseconds
            break
        }
    }

    $idleReached = $false
    try {
        $idleReached = $process.WaitForInputIdle($IdleTimeoutMs)
    }
    catch {
        $idleReached = $false
    }

    $idleMs = $sw.ElapsedMilliseconds

    $results += [pscustomobject]@{
        Run = $run
        WindowMs = $windowMs
        InputIdleMs = $idleMs
        InputIdleReached = $idleReached
        ExitedEarly = $process.HasExited
        ExePath = $ExePath
    }

    if (-not $process.HasExited) {
        Stop-Process -Id $process.Id -Force
    }

    Start-Sleep -Seconds $CooldownSeconds
}

$results | Format-Table -AutoSize

if ($CsvPath) {
    $results | Export-Csv -Path $CsvPath -NoTypeInformation
    Write-Host "Saved results to $CsvPath"
}
