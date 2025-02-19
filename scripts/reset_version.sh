#!/bin/bash

# Function to check if command succeeded
check_command() {
    if [ $? -ne 0 ]; then
        echo "Error: $1"
        exit 1
    fi
}

echo "Deleting local tags..."
git tag | xargs git tag -d
check_command "Failed to delete local tags"

echo "Deleting remote tags..."
git ls-remote --tags origin | cut -f2 | xargs -n1 git push origin --delete
check_command "Failed to delete remote tags"

echo "Resetting version to 0.1.0..."
poetry version 0.1.0
check_command "Failed to update version"

echo "Creating new CHANGELOG.md..."
cat > CHANGELOG.md << EOL
# Changelog

## [0.1.0] - 2025-02-13

### Initial Release
* Initial version of langchain-prolog
* Basic Prolog integration with LangChain
* Support for Prolog queries as runnables and tools
EOL
check_command "Failed to create CHANGELOG.md"

echo "Committing changes..."
git add pyproject.toml CHANGELOG.md
git commit -m "chore: reset version to 0.1.0"
check_command "Failed to commit changes"

echo "Pushing changes..."
git push origin main
check_command "Failed to push changes"

echo "Version reset complete!"
