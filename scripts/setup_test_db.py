#!/usr/bin/env python3
"""
DEPRECATED: This script creates a separate test database.
We now use schema separation instead for simpler configuration.

Use scripts/setup_test_schema.py instead.
"""

import sys

def main():
    print("⚠️  DEPRECATED: This script is no longer used.")
    print("🔧 We now use schema separation instead of separate databases.")
    print("📝 Please use: python scripts/setup_test_schema.py")
    print("\n🎯 Schema separation benefits:")
    print("   - Simpler configuration")
    print("   - No need to create extra databases")
    print("   - Faster test setup")
    print("   - Same isolation guarantees")
    sys.exit(1)

if __name__ == "__main__":
    main()
