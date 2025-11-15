import * as pulumi from "@pulumi/pulumi";

/**
 * Branded types for security-sensitive values
 * These ensure type safety at compile time and prevent mixing of incompatible string types
 */
type StackName = string & { readonly __brand: 'StackName' };
type HomelabFlag = '0' | '1';

/**
 * Validate HOMELAB environment variable
 * @throws {Error} if HOMELAB !== '1'
 */
function validateHomelabAccess(): void {
    const homelabFlag = (process.env.HOMELAB || '0') as HomelabFlag;

    if (homelabFlag !== '1') {
        throw new Error(
            `Refusing Pulumi operations: HOMELAB != 1 (got ${homelabFlag})\n` +
            `Set HOMELAB=1 to enable infrastructure operations on trusted machines.`
        );
    }
}

/**
 * Main infrastructure stack
 * All operations are gated by HOMELAB=1 check
 */
async function main(): Promise<void> {
    // CRITICAL: Validate HOMELAB access before any infrastructure operations
    validateHomelabAccess();

    const stackName = pulumi.getStack() as StackName;
    const projectName = pulumi.getProject();

    // Log configuration (safe for logging, no secrets)
    pulumi.log.info(`Initializing Pulumi stack: ${projectName}/${stackName}`);
    pulumi.log.info(`HOMELAB access validated`);

    // Example: Create a simple output to verify stack setup
    const metadata: Readonly<Record<string, pulumi.Output<string>>> = {
        stackName: pulumi.output(stackName),
        projectName: pulumi.output(projectName),
        timestamp: pulumi.output(new Date().toISOString()),
    };

    // Export typed outputs (immutable)
    Object.entries(metadata).forEach(([key, value]) => {
        exports[key] = value;
    });
}

export const outputs = main();

// Execute main with error handling
main().catch((err: Error) => {
    pulumi.log.error(`Fatal error: ${err.message}`);
    process.exit(1);
});
