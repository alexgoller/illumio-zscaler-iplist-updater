#!/usr/bin/env python3
"""
Script to fetch Zscaler IP addresses and update an Illumio Core IPList.

This script fetches IP addresses from the Zscaler API and creates or updates
an IPList in Illumio Core using the illumio Python package.
"""

import argparse
import os
import sys
import requests
from typing import List, Dict, Any
from illumio import PolicyComputeEngine, IPList, IPRange

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, will rely on environment variables


ZSCALER_API_URL = "https://config.zscaler.com/api/zscaler.net/future/json"


def fetch_zscaler_ips() -> List[str]:
    """
    Fetch IP addresses from Zscaler API.

    Returns:
        List of IP CIDR ranges
    """
    try:
        print(f"Fetching IP addresses from {ZSCALER_API_URL}...")
        response = requests.get(ZSCALER_API_URL, timeout=30)
        response.raise_for_status()

        data = response.json()
        prefixes = data.get('prefixes', [])

        print(f"Successfully fetched {len(prefixes)} IP ranges from Zscaler")
        return prefixes

    except requests.exceptions.RequestException as e:
        print(f"Error fetching Zscaler IPs: {e}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, ValueError) as e:
        print(f"Error parsing Zscaler response: {e}", file=sys.stderr)
        sys.exit(1)


def compare_ip_ranges(existing_ip_ranges: List[IPRange], new_ip_ranges: List[str]) -> bool:
    """
    Compare existing IP ranges with new IP ranges.
    
    Args:
        existing_ip_ranges: List of IPRange objects from existing IPList
        new_ip_ranges: List of IP CIDR strings from Zscaler
    
    Returns:
        True if IP ranges are different, False if they're the same
    """
    # Extract from_ip values from existing IPRange objects and normalize
    existing_ips = sorted([ip_range.from_ip for ip_range in existing_ip_ranges if ip_range.from_ip])
    
    # Normalize new IP ranges (already strings)
    new_ips = sorted(new_ip_ranges)
    
    # Compare the sorted lists
    are_different = existing_ips != new_ips
    
    if are_different:
        print(f"IP ranges have changed:")
        print(f"  Existing: {len(existing_ips)} IP ranges")
        print(f"  New: {len(new_ips)} IP ranges")
        
        # Show what's different (optional - can be verbose)
        existing_set = set(existing_ips)
        new_set = set(new_ips)
        added = new_set - existing_set
        removed = existing_set - new_set
        
        if added:
            print(f"  Added: {len(added)} IP range(s)")
            if len(added) <= 10:
                for ip in sorted(added):
                    print(f"    + {ip}")
            else:
                for ip in sorted(list(added)[:10]):
                    print(f"    + {ip}")
                print(f"    ... and {len(added) - 10} more")
        
        if removed:
            print(f"  Removed: {len(removed)} IP range(s)")
            if len(removed) <= 10:
                for ip in sorted(removed):
                    print(f"    - {ip}")
            else:
                for ip in sorted(list(removed)[:10]):
                    print(f"    - {ip}")
                print(f"    ... and {len(removed) - 10} more")
    else:
        print(f"IP ranges are unchanged ({len(existing_ips)} IP ranges)")
    
    return are_different


def create_or_update_iplist(pce: PolicyComputeEngine, iplist_name: str, ip_ranges: List[str]) -> tuple[IPList, bool]:
    """
    Create or update an IPList in Illumio Core.
    
    This function compares existing IP ranges with new ones and only updates
    if they're different.

    Args:
        pce: PolicyComputeEngine instance
        iplist_name: Name of the IPList to create or update
        ip_ranges: List of IP CIDR ranges to add to the IPList
    
    Returns:
        Tuple of (IPList object, was_updated boolean)
    """
    try:
        # Search for existing IPList
        print(f"Searching for existing IPList: {iplist_name}...")
        iplists = pce.ip_lists.get(params={'name': iplist_name})

        # Prepare IP ranges using IPRange objects with from_ip parameter
        ip_ranges_objects = [IPRange(from_ip=ip_range) for ip_range in ip_ranges]

        if iplists:
            # Check if IP ranges have changed
            existing_iplist = iplists[0]
            print(f"Found existing IPList (href: {existing_iplist.href})")
            
            # Get existing IP ranges (handle case where ip_ranges might be None)
            existing_ip_ranges = existing_iplist.ip_ranges or []
            
            # Compare existing and new IP ranges
            needs_update = compare_ip_ranges(existing_ip_ranges, ip_ranges)
            
            if not needs_update:
                print(f"IPList '{iplist_name}' is already up to date. No update needed.")
                return existing_iplist, False
            
            # Update existing IPList
            print(f"Updating IPList with {len(ip_ranges)} IP ranges...")

            # Update the IPList using IPList object
            updated_iplist_data = IPList(
                name=iplist_name,
                description='Zscaler IP ranges - Auto-updated',
                ip_ranges=ip_ranges_objects
            )
            
            # Update the IPList (may return None, so we'll fetch it if needed)
            pce.ip_lists.update(existing_iplist.href, updated_iplist_data)
            
            # Fetch the updated IPList to get the current state
            updated_iplist = pce.ip_lists.get_by_reference(existing_iplist.href)
            
            print(f"Successfully updated IPList: {iplist_name}")
            print(f"IPList href: {updated_iplist.href}")
            return updated_iplist, True
        else:
            # Create new IPList
            print(f"IPList not found. Creating new IPList: {iplist_name}...")

            # Create IPList using IPList object
            new_iplist_data = IPList(
                name=iplist_name,
                description='Zscaler IP ranges - Auto-updated',
                ip_ranges=ip_ranges_objects
            )
            new_iplist = pce.ip_lists.create(new_iplist_data)
            print(f"Successfully created IPList: {iplist_name}")
            print(f"IPList href: {new_iplist.href}")
            return new_iplist, True

    except Exception as e:
        print(f"Error creating/updating IPList: {e}", file=sys.stderr)
        sys.exit(1)

def provision_policy_changes(pce: PolicyComputeEngine, iplist_href: str):
    """
    Provision the policy changes for the IPList.
    """
    print(f"Provisioning policy changes for IPList: {iplist_href}...")
    try:
        changeset = pce.provision_policy_changes(
            change_description=f'Provision Zscaler IPList: {iplist_href}',
            hrefs=[iplist_href]
        )
        print(f"Successfully provisioned policy changes")
        print(f"Policy version: {changeset.version}")
        print(f"Workloads affected: {changeset.workloads_affected}")
    except Exception as e:
        print(f"Error provisioning policy changes: {e}", file=sys.stderr)

def main():
    """Main function to orchestrate the script."""
    parser = argparse.ArgumentParser(
        description='Fetch Zscaler IPs and update Illumio Core IPList',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Environment Variables:
  ILLUMIO_PCE_HOST      Illumio PCE hostname (e.g., pce.company.com)
  ILLUMIO_API_KEY       Illumio API key
  ILLUMIO_API_SECRET    Illumio API secret
  ILLUMIO_ORG_ID        Illumio organization ID (REQUIRED - typically 1 for most installations)
  ILLUMIO_PORT          Illumio PCE port (default: 443)

Examples:
  # Using environment variables (recommended)
  export ILLUMIO_PCE_HOST=pce.company.com
  export ILLUMIO_API_KEY=api_key_here
  export ILLUMIO_API_SECRET=api_secret_here
  export ILLUMIO_ORG_ID=1
  python update_zscaler_iplist.py --iplist-name "Zscaler IPs"

  # Using command line arguments
  python update_zscaler_iplist.py \\
    --pce-host pce.company.com \\
    --api-key api_key_here \\
    --api-secret api_secret_here \\
    --org-id 1 \\
    --iplist-name "Zscaler IPs"
        '''
    )

    # Illumio credentials
    parser.add_argument(
        '--pce-host',
        help='Illumio PCE hostname',
        default=os.environ.get('ILLUMIO_PCE_HOST')
    )
    parser.add_argument(
        '--api-key',
        help='Illumio API key',
        default=os.environ.get('ILLUMIO_API_KEY')
    )
    parser.add_argument(
        '--api-secret',
        help='Illumio API secret',
        default=os.environ.get('ILLUMIO_API_SECRET')
    )
    parser.add_argument(
        '--org-id',
        help='Illumio organization ID (REQUIRED - typically 1 for single-org PCE)',
        type=int,
        default=int(os.environ.get('ILLUMIO_ORG_ID', 1))
    )
    parser.add_argument(
        '--port',
        help='Illumio PCE port (default: 443)',
        type=int,
        default=os.environ.get('ILLUMIO_PORT', 443)
    )

    # IPList name (required)
    parser.add_argument(
        '--iplist-name',
        required=True,
        help='Name of the Illumio IPList to create or update'
    )

    # Optional: disable SSL verification
    parser.add_argument(
        '--no-verify-ssl',
        action='store_true',
        help='Disable SSL certificate verification (not recommended for production)'
    )

    args = parser.parse_args()

    # Validate required arguments
    if not args.pce_host:
        print("Error: --pce-host or ILLUMIO_PCE_HOST environment variable is required", file=sys.stderr)
        sys.exit(1)
    if not args.api_key:
        print("Error: --api-key or ILLUMIO_API_KEY environment variable is required", file=sys.stderr)
        sys.exit(1)
    if not args.api_secret:
        print("Error: --api-secret or ILLUMIO_API_SECRET environment variable is required", file=sys.stderr)
        sys.exit(1)

    # Fetch Zscaler IPs
    ip_ranges = fetch_zscaler_ips()

    # Display org_id being used
    if not os.environ.get('ILLUMIO_ORG_ID') and args.org_id == 1:
        print(f"\nUsing default organization ID: {args.org_id}")
        print("  (Set ILLUMIO_ORG_ID environment variable or use --org-id to specify)")
    else:
        print(f"\nUsing organization ID: {args.org_id}")

    # Connect to Illumio PCE
    print(f"Connecting to Illumio PCE at {args.pce_host}:{args.port}...")
    try:
        pce = PolicyComputeEngine(
            args.pce_host,
            port=args.port,
            org_id=args.org_id
        )
        pce.set_credentials(args.api_key, args.api_secret)

        if args.no_verify_ssl:
            print("Warning: SSL verification disabled")
            pce.set_tls_settings(verify=False)
        

        print(f"Successfully connected to Illumio PCE (Org ID: {args.org_id})")
    except Exception as e:
        print(f"Error connecting to Illumio PCE: {e}", file=sys.stderr)
        sys.exit(1)

    # Create or update IPList
    iplist, was_updated = create_or_update_iplist(pce, args.iplist_name, ip_ranges)
    print(f"IPList href: {iplist.href}")
    
    # Only provision if the IPList was actually updated
    if was_updated:
        print("\nProvisioning policy changes...")
        provision_policy_changes(pce, iplist.href)
        print("\n✓ Script completed successfully!")
    else:
        print("\n✓ Script completed successfully (no changes to provision)!")

if __name__ == '__main__':
    main()