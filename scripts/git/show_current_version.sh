#!/bin/bash

# Get the latest tag
latest_tag=$(git describe --tags $(git rev-list --tags --max-count=1))

# Output the latest tag
echo "Current version: $latest_tag"