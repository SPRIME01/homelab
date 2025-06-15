#!/usr/bin/env python3
"""
Example deployment script for Supabase infrastructure.
Demonstrates how to deploy Supabase to K3s cluster using the infrastructure module.
"""

import asyncio
from pathlib import Path

from infrastructure.supabase import SupabaseInfrastructure


async def deploy_supabase_example():
    """Deploy Supabase stack to K3s cluster."""
    print("🚀 Starting Supabase deployment example...")

    # Initialize Supabase infrastructure
    kubeconfig_path = Path.home() / ".kube" / "config"

    if not kubeconfig_path.exists():
        print(f"❌ Kubeconfig not found at {kubeconfig_path}")
        print("   Make sure K3s is installed and kubeconfig is properly configured")
        return False

    print(f"📋 Using kubeconfig: {kubeconfig_path}")

    try:
        # Create Supabase infrastructure manager
        supabase = SupabaseInfrastructure(kubeconfig_path)

        # Deploy the complete stack
        print("🏗️ Deploying Supabase components...")
        components = supabase.deploy_supabase_stack()

        print("✅ Supabase deployment completed successfully!")
        print("\n📊 Deployed components:")
        for name, component in components.items():
            print(f"  • {name}: {type(component).__name__}")

        print("\n🌐 Next steps:")
        print("  1. Wait for all pods to be ready: kubectl get pods -n supabase")
        print("  2. Check service health: make supabase-health")
        print(
            "  3. Access PostgreSQL: kubectl port-forward -n supabase svc/supabase-postgres-service 5432:5432"
        )
        print(
            "  4. Access API Gateway: kubectl port-forward -n supabase svc/supabase-kong-service 8000:8000"
        )

        return True

    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("  • Check K3s cluster status: kubectl get nodes")
        print("  • Verify cluster resources: kubectl top nodes")
        print(
            "  • Review deployment logs: kubectl logs -n supabase deployment/supabase-postgres"
        )
        return False


async def main():
    """Main deployment function."""
    success = await deploy_supabase_example()

    if success:
        print("\n🎉 Supabase is ready for use!")
        print("   Check the health status with: make supabase-health")
    else:
        print("\n⚠️  Deployment failed. Check the error messages above.")


if __name__ == "__main__":
    asyncio.run(main())
