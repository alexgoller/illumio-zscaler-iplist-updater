# Illumio Zscaler IPList Updater

Automatically fetch Zscaler IP addresses from their public API and update an Illumio Core IPList. This script intelligently compares existing IP ranges with new ones and only updates when changes are detected, minimizing unnecessary policy provisions.

## Overview

This script fetches the latest IP addresses from Zscaler's public API (`https://config.zscaler.com/api/zscaler.net/future/json`) and creates or updates an IPList in Illumio Core. It includes intelligent change detection, so it only updates the IPList and provisions policy changes when the IP ranges have actually changed.

### Key Features

- 🔄 **Automatic IP List Synchronization**: Fetches latest Zscaler IP ranges from official API
- 🔍 **Intelligent Change Detection**: Compares existing IP ranges with new ones before updating
- ⚡ **Efficient Updates**: Only updates and provisions when changes are detected
- 📊 **Change Reporting**: Shows added/removed IP ranges when updates occur
- 🆕 **Auto-Creation**: Creates new IPList if it doesn't exist
- 🔄 **Auto-Provisioning**: Automatically provisions policy changes after updates
- 🌐 **IPv4 & IPv6 Support**: Handles both IPv4 and IPv6 addresses
- 🔒 **Secure**: Supports environment variables for credential management
- 📝 **Comprehensive Logging**: Detailed output showing what the script is doing

## Installation

### Prerequisites

- Python 3.7 or higher
- Illumio Core PCE access with API credentials
- Network access to both Zscaler API and Illumio PCE

### Setup

1. Clone this repository:

```bash
git clone <repository-url>
cd illumio-zscaler-iplist-updater
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) Set up environment variables using a `.env` file:

```bash
cp .env.example .env
# Edit .env with your Illumio PCE credentials
```

## Usage

### Configuration Options

You can provide credentials via environment variables or command-line arguments. Environment variables are recommended for security, especially when scheduling the script.

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ILLUMIO_PCE_HOST` | Illumio PCE hostname (e.g., `pce.company.com`) | Yes | - |
| `ILLUMIO_API_KEY` | Illumio API key username | Yes | - |
| `ILLUMIO_API_SECRET` | Illumio API key secret | Yes | - |
| `ILLUMIO_ORG_ID` | Illumio organization ID | Yes | `1` |
| `ILLUMIO_PORT` | Illumio PCE port | No | `443` |

### Command-Line Arguments

| Argument | Environment Variable | Required | Default | Description |
|----------|---------------------|----------|---------|-------------|
| `--pce-host` | `ILLUMIO_PCE_HOST` | Yes* | - | Illumio PCE hostname |
| `--api-key` | `ILLUMIO_API_KEY` | Yes* | - | Illumio API key username |
| `--api-secret` | `ILLUMIO_API_SECRET` | Yes* | - | Illumio API key secret |
| `--org-id` | `ILLUMIO_ORG_ID` | No | `1` | Illumio organization ID |
| `--port` | `ILLUMIO_PORT` | No | `443` | Illumio PCE port |
| `--iplist-name` | - | **Yes** | - | Name of the IPList to create/update |
| `--no-verify-ssl` | - | No | `False` | Disable SSL certificate verification |

*At least one method (environment variable or command-line argument) must be provided for each required credential.

### Usage Examples

#### Option 1: Using .env file (Recommended)

The script automatically loads variables from a `.env` file if `python-dotenv` is installed:

```bash
# Create .env file
cat > .env << EOF
ILLUMIO_PCE_HOST=pce.company.com
ILLUMIO_API_KEY=your_api_key_username
ILLUMIO_API_SECRET=your_api_secret
ILLUMIO_ORG_ID=1
ILLUMIO_PORT=443
EOF

# Run the script
python update_zscaler_iplist.py --iplist-name "Zscaler IPs"
```

#### Option 2: Using Exported Environment Variables

```bash
export ILLUMIO_PCE_HOST=pce.company.com
export ILLUMIO_API_KEY=your_api_key_username
export ILLUMIO_API_SECRET=your_api_secret
export ILLUMIO_ORG_ID=1
export ILLUMIO_PORT=443

python update_zscaler_iplist.py --iplist-name "Zscaler IPs"
```

#### Option 3: Using Command-Line Arguments

```bash
python update_zscaler_iplist.py \
  --pce-host pce.company.com \
  --api-key your_api_key_username \
  --api-secret your_api_secret \
  --org-id 1 \
  --port 443 \
  --iplist-name "Zscaler IPs"
```

#### Option 4: Mixed (Environment Variables + Command-Line)

```bash
# Set most credentials via environment
export ILLUMIO_PCE_HOST=pce.company.com
export ILLUMIO_API_KEY=your_api_key_username
export ILLUMIO_API_SECRET=your_api_secret

# Override org-id via command line
python update_zscaler_iplist.py --org-id 2 --iplist-name "Zscaler IPs"
```

### Important Notes

#### Organization ID

The organization ID (`--org-id` or `ILLUMIO_ORG_ID`) is **crucial** for connecting to your Illumio instance:

- For single-organization PCE installations, this is typically `1`
- For multi-organization PCEs, you'll need the specific org ID for your organization
- You can find your org ID in the Illumio PCE web console URL: `https://pce.company.com/orgs/<org_id>/`
- If unsure, check with your Illumio administrator or look at your API endpoint URLs
- The script defaults to `1` if not specified

#### SSL Verification

By default, the script verifies SSL certificates. If you're using self-signed certificates or encountering SSL issues, you can disable verification with `--no-verify-ssl`:

```bash
python update_zscaler_iplist.py --iplist-name "Zscaler IPs" --no-verify-ssl
```

**⚠️ Warning**: Disabling SSL verification is not recommended for production environments as it reduces security.

## How It Works

1. **Fetch IPs**: Connects to Zscaler's public API and fetches the latest IP ranges
2. **Check Existing**: Searches for an existing IPList with the specified name
3. **Compare**: If the IPList exists, compares existing IP ranges with new ones
4. **Update if Changed**: Only updates the IPList if IP ranges have changed
5. **Provision**: Provisions policy changes only if an update occurred
6. **Report**: Shows detailed information about changes (added/removed IPs)

### Example Output

#### When IPs Have Changed:

```
Fetchin