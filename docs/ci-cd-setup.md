# CI/CD Setup for MailScout

This document explains how to set up the Continuous Integration/Continuous Deployment (CI/CD) pipeline for MailScout.

## GitHub Actions Workflows

MailScout uses GitHub Actions for automated testing, building, and deployment. There are two main workflows:

1. **Main CI Workflow** (`main.yml`) - Runs tests and builds the package when changes are pushed to the main branch
2. **Deployment Workflow** (`deploy.yml`) - Deploys the application to a test server after successful CI run

## Required Secrets

To make the deployment pipeline work, you need to set up the following secrets in your GitHub repository:

### SSH Deployment Secrets

- `SSH_PRIVATE_KEY`: The private SSH key used to connect to the deployment server
- `DEPLOY_HOST`: The hostname or IP address of the deployment server
- `DEPLOY_USER`: The username for SSH access to the deployment server
- `DEPLOY_PATH`: The path on the deployment server where files should be deployed
- `API_PORT`: The port on which the MailScout API runs (used for health checks)

## Setting Up GitHub Secrets

1. Navigate to your GitHub repository
2. Go to **Settings** > **Secrets and variables** > **Actions**
3. Click on **New repository secret**
4. Add each of the required secrets:

### SSH Key Setup

To generate a new SSH key for deployment:

```bash
# Generate a new ED25519 key (preferred for GitHub Actions)
ssh-keygen -t ed25519 -C "mailscout-deploy-key" -f mailscout_deploy_key

# Display the private key to copy to GitHub Secrets
cat mailscout_deploy_key

# Display the public key to add to the server's authorized_keys
cat mailscout_deploy_key.pub
```

Copy the private key to the `SSH_PRIVATE_KEY` secret in GitHub. Then add the public key to the `~/.ssh/authorized_keys` file on your deployment server.

## Server Setup

The deployment script assumes a few things about your server:

1. Python 3.8+ is installed
2. The application runs as a systemd service named `mailscout`
3. The deploying user has sudo privileges to restart the service

### Creating a Systemd Service

Create a systemd service file at `/etc/systemd/system/mailscout.service`:

```ini
[Unit]
Description=MailScout Email Processing Service
After=network.target

[Service]
User=<service_user>
WorkingDirectory=/path/to/mailscout
ExecStart=/path/to/mailscout/venv/bin/python run.py --host 0.0.0.0 --port 8000
Restart=on-failure
Environment="PYTHONPATH=/path/to/mailscout"

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mailscout
sudo systemctl start mailscout
```

## Troubleshooting

### Deployment Failures

If the deployment fails, check:

1. SSH key permissions and setup
2. Server connectivity
3. GitHub Actions logs for detailed error messages

### Verification Failures

If the verification step fails:

1. Check if the service is running: `sudo systemctl status mailscout`
2. Check service logs: `sudo journalctl -u mailscout`
3. Ensure the port is accessible and not blocked by a firewall