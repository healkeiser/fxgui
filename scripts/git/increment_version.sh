#!/bin/bash

# Get the latest tag
latest_tag=$(git describe --tags `git rev-list --tags --max-count=1`)

# Split the version into an array
IFS='.' read -r -a version_parts <<< "$latest_tag"

# Increment the version based on the argument
case $1 in
  major)
    ((version_parts[0]++))
    version_parts[1]=0
    version_parts[2]=0
    ;;
  minor)
    ((version_parts[1]++))
    version_parts[2]=0
    ;;
  patch)
    ((version_parts[2]++))
    ;;
  *)
    echo "Usage: $0 {major|minor|patch}"
    exit 1
    ;;
esac

# Join the version parts into a new version string
new_version="${version_parts[0]}.${version_parts[1]}.${version_parts[2]}"

# Output the new version
echo $new_version