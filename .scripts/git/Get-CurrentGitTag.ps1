# Get the latest tag
$latestTag = git describe --tags (git rev-list --tags --max-count=1)

# Output the latest tag
Write-Output "Current version: $latestTag"