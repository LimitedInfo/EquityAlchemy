# Secrets and Credentials Security

This project uses pre-commit hooks to help prevent accidentally committing sensitive information to the repository. The following security measures are in place:

## Pre-commit hooks

The project uses [pre-commit](https://pre-commit.com/) with the following hooks:

- **detect-secrets**: Scans for potential secrets or credentials in the codebase
- **trailing-whitespace**: Removes trailing whitespace
- **end-of-file-fixer**: Ensures files end with a newline
- **check-yaml**: Validates YAML files
- **check-added-large-files**: Prevents large files from being committed

## Setup

1. The pre-commit hooks are already installed and should run automatically before each commit.
2. If you make a new clone of the repository, you'll need to run: `pip install pre-commit detect-secrets` and then `pre-commit install`.

## Security best practices

- Keep sensitive information in `.env` files (which are gitignored)
- Never commit API keys, passwords, or other credentials directly in code
- Use environment variables for sensitive configuration
- Consider using a secrets management service for production environments

## What to do if you accidentally commit secrets

If you accidentally commit sensitive information:

1. Change the compromised secret immediately
2. Remove the secret from git history using tools like `git filter-branch` or BFG Repo-Cleaner
3. Force push the changes to remove the secret from the repository history

## Testing the hooks

You can manually run the pre-commit hooks using:

```bash
pre-commit run --all-files
```
