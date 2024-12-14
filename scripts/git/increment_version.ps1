# Get the latest tag
$latestTag = git describe --tags (git rev-list --tags --max-count=1)

# Split the version into an array
$versionParts = $latestTag -split '\.'

# Increment the version based on the argument
param (
    [string]$incrementType
)

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

# Output the new version
Write-Output $newVersion