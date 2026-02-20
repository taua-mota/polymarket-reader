# .build.ps1 — Invoke-Build script for Polymarket Position Monitor
# Install Invoke-Build once with:  Install-Module InvokeBuild -Scope CurrentUser
# Then run tasks with:             Invoke-Build <task>  (or just: Invoke-Build)

$VenvPython = "$PSScriptRoot\venv\bin\python.exe"
$VenvPip    = "$PSScriptRoot\venv\bin\pip.exe"

# Default task — start the bot
task . Run

# ── Setup ────────────────────────────────────────────────────────────────────

# Create the virtual environment if it does not exist yet
task Venv {
    if (-not (Test-Path $VenvPython)) {
        Write-Build Cyan "Creating virtual environment..."
        python -m venv venv
    } else {
        Write-Build Green "Virtual environment already exists."
    }
}

# Install/upgrade all runtime + test dependencies
task Install Venv, {
    Write-Build Cyan "Installing dependencies..."
    & $VenvPip install -r requirements.txt pytest pytest-asyncio --only-binary :all: -q
    Write-Build Green "Dependencies installed."
}

# ── Development ──────────────────────────────────────────────────────────────

# Run the bot (Ctrl-C to stop)
task Run {
    if (-not (Test-Path $VenvPython)) { throw "Run 'Invoke-Build Install' first." }
    if (-not (Test-Path "$PSScriptRoot\.env")) { throw ".env not found. Copy .env.example to .env and fill in your credentials." }
    Write-Build Cyan "Starting Polymarket Position Monitor (Ctrl-C to stop)..."
    & $VenvPython -m src.main
}

# Run the test suite
task Test {
    if (-not (Test-Path $VenvPython)) { throw "Run 'Invoke-Build Install' first." }
    Write-Build Cyan "Running tests..."
    & $VenvPython -m pytest tests/ -v
}

# Run tests and treat deprecation warnings as errors
task TestStrict {
    if (-not (Test-Path $VenvPython)) { throw "Run 'Invoke-Build Install' first." }
    Write-Build Cyan "Running strict tests..."
    & $VenvPython -m pytest tests/ -v -W error::DeprecationWarning
}

# ── Housekeeping ─────────────────────────────────────────────────────────────

# Remove generated/runtime files
task Clean {
    Write-Build Yellow "Cleaning up..."
    $targets = @('data\state.json', '.pytest_cache', 'src\__pycache__', 'src\agents\__pycache__', 'src\utils\__pycache__', 'tests\__pycache__')
    foreach ($t in $targets) { Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $t }
    Write-Build Green "Clean complete."
}

# Full reset: clean + reinstall
task Reset Clean, Install
