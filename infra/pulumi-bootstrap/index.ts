import * as pulumi from "@pulumi/pulumi";

/**
 * Branded types for security-sensitive values
 * These ensure type safety at compile time and prevent mixing of incompatible string types
 */
type StackName = string & { readonly __brand: 'StackName' };
type ResourceID = string & { readonly __brand: 'ResourceID' };
type HomelabFlag = '0' | '1';

/**
 * Discriminated union for command execution results
 * Enables exhaustive pattern matching and type-safe error handling
 */
type CommandResult<T> =
    | { readonly status: 'success'; readonly data: T }
    | { readonly status: 'error'; readonly error: Error; readonly exitCode: number }
    | { readonly status: 'skipped'; readonly reason: string };

/**
 * Validate HOMELAB environment variable
 * @throws {Error} if HOMELAB !== '1'
 */
function validateHomelabAccess(): asserts process is { env: { HOMELAB: '1' } } {
    const homelabFlag = (process.env.HOMELAB || '0') as HomelabFlag;

    if (homelabFlag !== '1') {
        throw new Error(
            `Refusing Pulumi operations: HOMELAB != 1 (got ${homelabFlag})\n` +
            `Set HOMELAB=1 to enable infrastructure operations on trusted machines.`
        );
    }
}

/**
 * Type guard for validating branded ResourceID
 */
function isValidResourceID(value: string): value is ResourceID {
    return /^[a-z][a-z0-9-]{0,62}$/.test(value);
}

/**
 * Create a branded ResourceID with runtime validation
 */
function createResourceID(raw: string): ResourceID {
    if (!isValidResourceID(raw)) {
        throw new Error(
            `Invalid resource ID: "${raw}". Must match ^[a-z][a-z0-9-]{0,62}$`
        );
    }
    return raw as ResourceID;
}

/**
 * Main infrastructure stack
 * All operations are gated by HOMELAB=1 check
 */
async function main(): Promise<void> {
    // CRITICAL: Validate HOMELAB access before any infrastructure operations
    validateHomelabAccess();

    const config = new pulumi.Config();
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
    return pulumi.all(metadata).apply((resolved) => {
        Object.entries(resolved).forEach(([key, value]) => {
            pulumi.export(key, value);
        });
    });
}

// Execute main with error handling
main().catch((err: Error) => {
    pulumi.log.error(`Fatal error: ${err.message}`);
    process.exit(1);
});
