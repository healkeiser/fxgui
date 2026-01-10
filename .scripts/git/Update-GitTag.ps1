param (
    [string]$incrementType
)

# Get the latest tag (handle case where no tags exist)
try {
    $tagList = git rev-list --tags --max-count=1 2>$null
    if ($tagList) {
        $latestTag = git describe --tags $tagList 2>$null
    }
    else {
        $latestTag = $null
    }
}
catch {
    $latestTag = $null
}

# If no tags exist, start with v0.1.0
if (-not $latestTag) {
    Write-Host "No existing tags found. Creating initial version v0.1.0..."
    $newVersion = "0.1.0"
    git tag -a "v$newVersion" -m "Version $newVersion"
    git push origin "v$newVersion"
    Write-Host "Tag v$newVersion pushed. CI will update package.py, create the release, and send Slack notification."
    Write-Output $newVersion
    exit 0
}

# Remove the 'v' prefix if it exists
if ($latestTag.StartsWith('v')) {
    $latestTag = $latestTag.Substring(1)
}

# Split the version into an array
$versionParts = $latestTag -split '\.'

# Ensure the versionParts array has three elements
if ($versionParts.Length -ne 3) {
    Write-Host "Error: The latest tag '$latestTag' is not in the expected format 'vX.Y.Z'."
    exit 1
}

# ? Check all the tags follow the format vX.Y.Z by running the following command:
# ? `git show-ref --tags`

switch ($incrementType) {
    "major" {
        $versionParts[0] = [int]$versionParts[0] + 1
        $versionParts[1] = 0
        $versionParts[2] = 0
    }
    "minor" {
        $versionParts[1] = [int]$versionParts[1] + 1
        $versionParts[2] = 0
    }
    "patch" {
        $versionParts[2] = [int]$versionParts[2] + 1
    }
    default {
        Write-Host "Usage: .\increment_version.ps1 {major|minor|patch}"
        exit 1
    }
}

# Join the version parts into a new version string
$newVersion = "$($versionParts[0]).$($versionParts[1]).$($versionParts[2])"

# Create and push the new tag (CI will handle package.py update)
git tag -a "v$newVersion" -m "Version $newVersion"
git push origin "v$newVersion"

Write-Host "Tag v$newVersion pushed. CI will update package.py, create the release, and send Slack notification."

# Output the new version
Write-Output $newVersion