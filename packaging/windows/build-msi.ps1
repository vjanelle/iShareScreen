param(
    [switch] $SkipExeBuild
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$distDir = Join-Path $projectRoot 'dist'
$exePath = Join-Path $distDir 'iShareScreen.exe'
$wixProject = Join-Path $PSScriptRoot 'isharescreen.wixproj'
$projectFile = Join-Path $projectRoot 'pyproject.toml'
$versionMatch = [regex]::Match(
    (Get-Content -LiteralPath $projectFile -Raw),
    '(?m)^version\s*=\s*"(?<version>\d+\.\d+\.\d+)"'
)
if (-not $versionMatch.Success) {
    throw 'pyproject.toml must define a numeric MAJOR.MINOR.PATCH version for MSI builds.'
}
$productVersion = $versionMatch.Groups['version'].Value

$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not $SkipExeBuild) {
    $pythonCandidates = [System.Collections.Generic.List[string]]::new()
    if ($env:VIRTUAL_ENV) {
        $pythonCandidates.Add((Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe'))
    }
    $pythonCandidates.Add((Join-Path $projectRoot '.venv\Scripts\python.exe'))
    $pythonCandidates.Add((Join-Path (Split-Path $projectRoot -Parent) '.venv\Scripts\python.exe'))
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $pythonCandidates.Add($pythonCommand.Source)
    }

    $python = $null
    foreach ($candidate in ($pythonCandidates | Select-Object -Unique)) {
        if (Test-Path -LiteralPath $candidate) {
            & $candidate -c 'import PyInstaller' 2>$null
            if ($LASTEXITCODE -eq 0) {
                $python = $candidate
                break
            }
        }
    }
    if (-not $python) {
        throw 'Python with PyInstaller was not found. Install the windows-build extra in .venv or activate that environment.'
    }
    Push-Location $projectRoot
    try {
        & $python -m PyInstaller --noconfirm --clean packaging/windows/isharescreen.spec
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path -LiteralPath $exePath)) {
    throw "Missing $exePath. Build the EXE first or omit -SkipExeBuild."
}

$buildDir = Join-Path $projectRoot 'build\msi'
New-Item -ItemType Directory -Path $buildDir -Force | Out-Null
$licenseText = [System.IO.File]::ReadAllText((Join-Path $projectRoot 'LICENSE'), [System.Text.Encoding]::UTF8)
$rtf = [System.Text.StringBuilder]::new()
[void] $rtf.Append('{\rtf1\ansi\deff0{\fonttbl{\f0\fswiss Segoe UI;}}\f0\fs18 ')
foreach ($character in $licenseText.ToCharArray()) {
    $code = [int] $character
    if ($character -eq "`r") {
        continue
    }
    if ($character -eq "`n") {
        [void] $rtf.Append('\par' + "`n")
    }
    elseif ($character -eq '\' -or $character -eq '{' -or $character -eq '}') {
        [void] $rtf.Append('\' + $character)
    }
    elseif ($character -eq "`t") {
        [void] $rtf.Append('\tab ')
    }
    elseif ($code -gt 127) {
        if ($code -gt 32767) { $code -= 65536 }
        [void] $rtf.Append("\u$code?")
    }
    else {
        [void] $rtf.Append($character)
    }
}
[void] $rtf.Append('}')
$licenseRtf = Join-Path $buildDir 'AGPL-3.0.rtf'
[System.IO.File]::WriteAllText($licenseRtf, $rtf.ToString(), [System.Text.Encoding]::ASCII)

Push-Location $projectRoot
try {
    & dotnet build $wixProject --configuration Release `
        "-p:ProductVersion=$productVersion" `
        "-p:PublishDir=$distDir" `
        "-p:LicenseRtf=$licenseRtf"
    if ($LASTEXITCODE -ne 0) {
        throw "WiX build failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

$msiPath = Join-Path $distDir 'iShareScreen.msi'
Write-Output "Created $msiPath"
