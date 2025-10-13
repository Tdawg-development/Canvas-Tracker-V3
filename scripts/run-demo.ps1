# Canvas Tracker V3 - Demo Runner Script
# Automatically discovers and runs demo files from canvas-interface/demos

param(
    [string]$DemoName = "",
    [switch]$List = $false,
    [switch]$Interactive = $false
)

# Get the project root directory
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DemosPath = Join-Path $ProjectRoot "canvas-interface\demos"

# Function to get all demo files
function Get-DemoFiles {
    if (-not (Test-Path $DemosPath)) {
        Write-Error "Demos directory not found: $DemosPath"
        exit 1
    }
    
    $demoFiles = Get-ChildItem -Path $DemosPath -Filter "*.ts" -File | Where-Object {
        $_.Name -notmatch "\.d\.ts$" # Exclude TypeScript declaration files
    }
    
    return $demoFiles
}

# Function to format demo name for display
function Format-DemoName {
    param([string]$fileName)
    
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
    # Convert kebab-case and snake_case to title case
    $words = $baseName -split "[-_]"
    $formatted = ($words | ForEach-Object { 
        if ($_.Length -gt 0) {
            $_.Substring(0,1).ToUpper() + $_.Substring(1).ToLower()
        }
    }) -join " "
    return $formatted
}

# Function to list all available demos
function Show-DemoList {
    $demoFiles = Get-DemoFiles
    
    if ($demoFiles.Count -eq 0) {
        Write-Host "No demo files found in $DemosPath" -ForegroundColor Yellow
        return
    }
    
    Write-Host "`nAvailable demos:" -ForegroundColor Green
    Write-Host "=================" -ForegroundColor Green
    
    for ($i = 0; $i -lt $demoFiles.Count; $i++) {
        $file = $demoFiles[$i]
        $displayName = Format-DemoName $file.Name
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        
        Write-Host "$($i + 1). $displayName" -ForegroundColor Cyan
        Write-Host "   File: $($file.Name)" -ForegroundColor Gray
        Write-Host "   Run:  npm run demo $baseName" -ForegroundColor Gray
        Write-Host ""
    }
}

# Function to run interactive demo selection
function Start-InteractiveMode {
    $demoFiles = Get-DemoFiles
    
    if ($demoFiles.Count -eq 0) {
        Write-Host "No demo files found in $DemosPath" -ForegroundColor Yellow
        return
    }
    
    Show-DemoList
    
    do {
        Write-Host "Enter demo number (1-$($demoFiles.Count)) or 'q' to quit: " -NoNewline -ForegroundColor Yellow
        $selection = Read-Host
        
        if ($selection -eq 'q' -or $selection -eq 'quit') {
            Write-Host "Goodbye!" -ForegroundColor Green
            return
        }
        
        $selectedIndex = $null
        if ([int]::TryParse($selection, [ref]$selectedIndex)) {
            if ($selectedIndex -ge 1 -and $selectedIndex -le $demoFiles.Count) {
                $selectedFile = $demoFiles[$selectedIndex - 1]
                $relativePath = "canvas-interface\demos\$($selectedFile.Name)"
                
                Write-Host "`nRunning demo: $(Format-DemoName $selectedFile.Name)" -ForegroundColor Green
                Write-Host "File: $relativePath" -ForegroundColor Gray
                Write-Host ("=" * 50) -ForegroundColor Gray
                
                # Run the demo
                $command = "ts-node `"$relativePath`""
                Invoke-Expression $command
                
                Write-Host ""
                Write-Host ("=" * 50) -ForegroundColor Gray
                Write-Host "Demo completed." -ForegroundColor Green
                return
            }
        }
        
        Write-Host "Invalid selection. Please enter a number between 1 and $($demoFiles.Count)." -ForegroundColor Red
    } while ($true)
}

# Function to run a specific demo
function Start-Demo {
    param([string]$demoName)
    
    $demoFiles = Get-DemoFiles
    
    # Try to find the demo file by name (with or without .ts extension)
    $targetFile = $demoFiles | Where-Object {
        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($_.Name)
        $baseName -eq $demoName -or $_.Name -eq $demoName
    }
    
    if (-not $targetFile) {
        Write-Host "Demo file not found: $demoName" -ForegroundColor Red
        Write-Host "`nAvailable demos:" -ForegroundColor Yellow
        $demoFiles | ForEach-Object {
            $baseName = [System.IO.Path]::GetFileNameWithoutExtension($_.Name)
            Write-Host "  - $baseName" -ForegroundColor Cyan
        }
        exit 1
    }
    
    $relativePath = "canvas-interface\demos\$($targetFile.Name)"
    
    Write-Host "Running demo: $(Format-DemoName $targetFile.Name)" -ForegroundColor Green
    Write-Host "File: $relativePath" -ForegroundColor Gray
    Write-Host ("=" * 50) -ForegroundColor Gray
    
    # Run the demo
    $command = "ts-node `"$relativePath`""
    Invoke-Expression $command
}

# Main execution logic
try {
    Set-Location $ProjectRoot
    
    if ($List) {
        Show-DemoList
    }
    elseif ($Interactive -or $DemoName -eq "") {
        Start-InteractiveMode
    }
    else {
        Start-Demo $DemoName
    }
}
catch {
    Write-Error "An error occurred: $($_.Exception.Message)"
    exit 1
}