# Canvas Tracker V3 - Git Commit Utility
# Streamlines git add + commit workflow with optional file specification

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Message,
    
    [Parameter(Mandatory=$false, Position=1)]
    [string[]]$Files = @("."),
    
    [Parameter(Mandatory=$false)]
    [switch]$DryRun,
    
    [Parameter(Mandatory=$false)]
    [switch]$VerboseMode
)

# Color output functions
function Write-Success { param($Text) Write-Host $Text -ForegroundColor Green }
function Write-Info { param($Text) Write-Host $Text -ForegroundColor Cyan }
function Write-Warning { param($Text) Write-Host $Text -ForegroundColor Yellow }
function Write-Error { param($Text) Write-Host $Text -ForegroundColor Red }

# Banner
Write-Info "Canvas Tracker V3 - Git Commit Utility"
Write-Info "========================================"

# Validate we're in a git repository
if (-not (Test-Path ".git")) {
    Write-Error "Error: Not in a git repository root directory"
    exit 1
}

# Show current git status
Write-Info "Current Git Status:"
git status --short

# Validate commit message
if ([string]::IsNullOrWhiteSpace($Message)) {
    Write-Error "Error: Commit message cannot be empty"
    exit 1
}

if ($Message.Length -lt 10) {
    Write-Warning "Warning: Commit message is quite short. Consider adding more detail."
}

# Show files to be added
Write-Info ""
Write-Info "Files to be added:"
foreach ($file in $Files) {
    if ($file -eq ".") {
        Write-Info "  * All modified files (.)"
    } else {
        Write-Info "  * $file"
    }
}

Write-Info ""
Write-Info "Commit message:"
Write-Info "  `"$Message`""

# Dry run mode
if ($DryRun) {
    Write-Warning "DRY RUN MODE - No actual git operations will be performed"
    Write-Info ""
    Write-Info "Would execute:"
    Write-Info "  git add $($Files -join ' ')"
    Write-Info "  git commit -m `"$Message`""
    Write-Info ""
    Write-Warning "Note: This follows our Git Workflow Protocol - commits locally only."
    Write-Warning "Remember: Get user verification before pushing to remote!"
    exit 0
}

# Confirmation prompt
Write-Info ""
$confirmation = Read-Host "Proceed with commit? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Warning "Commit cancelled by user"
    exit 0
}

# Execute git add
Write-Info ""
Write-Info "Adding files to staging..."
try {
    if ($VerboseMode) {
        git add $Files --verbose
    } else {
        git add $Files
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Git add failed with exit code $LASTEXITCODE"
    }
    
    Write-Success "Files added successfully"
} catch {
    Write-Error "Failed to add files: $_"
    exit 1
}

# Execute git commit
Write-Info "Creating commit..."
try {
    if ($VerboseMode) {
        git commit -m $Message --verbose
    } else {
        git commit -m $Message
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Git commit failed with exit code $LASTEXITCODE"
    }
    
    Write-Success "Commit created successfully"
} catch {
    Write-Error "Failed to create commit: $_"
    exit 1
}

# Success and reminder
Write-Info ""
Write-Success "Commit completed successfully!"
Write-Info "Commit message: `"$Message`""

# Git Workflow Protocol reminder
Write-Info ""
Write-Warning "Git Workflow Protocol Reminder:"
Write-Warning "   Changes committed LOCALLY only"
Write-Warning "   Get user verification before pushing to remote"
Write-Warning "   Use 'git push origin master' only after approval"

# Show recent commits
Write-Info ""
Write-Info "Recent commits:"
git log --oneline -5

Write-Info ""
Write-Success "Ready for verification and push!"