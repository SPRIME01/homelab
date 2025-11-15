/**
 * Branded types for security-sensitive values in homelab infrastructure
 * These types prevent mixing of different string types at compile time
 */

// Tailscale networking types
export type TailscaleIP = string & { readonly __brand: 'TailscaleIP' };
export type TailscaleMachineID = string & { readonly __brand: 'TailscaleMachineID' };

// SOPS/age encryption types
export type SOPSFilePath = string & { readonly __brand: 'SOPSFilePath' };
export type AgeRecipient = string & { readonly __brand: 'AgeRecipient' };
export type AgeIdentityPath = string & { readonly __brand: 'AgeIdentityPath' };

// Nx workspace types
export type NxProjectName = string & { readonly __brand: 'NxProjectName' };
export type NxTargetName = string & { readonly __brand: 'NxTargetName' };
export type NxAgentToken = string & { readonly __brand: 'NxAgentToken' };

// Environment flags
export type HomelabFlag = '0' | '1';

/**
 * Discriminated union for command execution results
 */
export type CommandResult<T> =
    | { readonly status: 'success'; readonly data: T }
    | { readonly status: 'error'; readonly error: Error; readonly exitCode: number }
    | { readonly status: 'skipped'; readonly reason: string };

/**
 * Type guard for Tailscale IP addresses (100.0.0.0/8 range)
 */
export function isTailscaleIP(value: string): value is TailscaleIP {
    // Check format: 100.x.x.x
    if (!/^100\.\d+\.\d+\.\d+$/.test(value)) {
        return false;
    }

    // Validate each octet is 0-255
    const octets = value.split('.').map(Number);
    return octets[0] === 100 && octets.slice(1).every(o => o >= 0 && o <= 255);
}

/**
 * Validates and creates a TailscaleIP branded type
 * @throws Error if the IP is invalid
 */
export function createTailscaleIP(raw: string): TailscaleIP {
    if (!isTailscaleIP(raw)) {
        throw new Error(`Invalid Tailscale IP: "${raw}". Expected 100.x.x.x format.`);
    }
    return raw as TailscaleIP;
}

/**
 * Type guard for age recipient public keys
 * Format: age1 followed by 58 base58 characters
 */
export function isAgeRecipient(value: string): value is AgeRecipient {
    return /^age1[a-z0-9]{58}$/.test(value);
}

/**
 * Validates and creates an AgeRecipient branded type
 * @throws Error if the recipient is invalid
 */
export function createAgeRecipient(raw: string): AgeRecipient {
    if (!isAgeRecipient(raw)) {
        throw new Error(`Invalid age recipient: "${raw}". Expected age1... format.`);
    }
    return raw as AgeRecipient;
}

/**
 * Type guard for SOPS file paths (must end with .sops)
 */
export function isSOPSFilePath(value: string): value is SOPSFilePath {
    return value.endsWith('.sops');
}

/**
 * Validates and creates a SOPSFilePath branded type
 * @throws Error if the path is invalid
 */
export function createSOPSFilePath(raw: string): SOPSFilePath {
    if (!isSOPSFilePath(raw)) {
        throw new Error(`Invalid SOPS file path: "${raw}". Must end with .sops`);
    }
    return raw as SOPSFilePath;
}

/**
 * Type guard for Nx project names (alphanumeric with hyphens)
 */
export function isNxProjectName(value: string): value is NxProjectName {
    return /^[a-z][a-z0-9-]{0,62}$/.test(value);
}

/**
 * Validates and creates an NxProjectName branded type
 * @throws Error if the name is invalid
 */
export function createNxProjectName(raw: string): NxProjectName {
    if (!isNxProjectName(raw)) {
        throw new Error(
            `Invalid Nx project name: "${raw}". Must start with lowercase letter, ` +
            `contain only lowercase letters, numbers, and hyphens, max 63 chars.`
        );
    }
    return raw as NxProjectName;
}

/**
 * Type guard for Nx target names (build, test, lint, etc.)
 */
export function isNxTargetName(value: string): value is NxTargetName {
    return /^[a-z][a-z0-9-:]{0,62}$/.test(value);
}

/**
 * Validates and creates an NxTargetName branded type
 * @throws Error if the name is invalid
 */
export function createNxTargetName(raw: string): NxTargetName {
    if (!isNxTargetName(raw)) {
        throw new Error(
            `Invalid Nx target name: "${raw}". Must start with lowercase letter, ` +
            `contain only lowercase letters, numbers, hyphens, and colons, max 63 chars.`
        );
    }
    return raw as NxTargetName;
}

/**
 * Validates HOMELAB environment flag
 */
export function isHomelabFlag(value: string): value is HomelabFlag {
    return value === '0' || value === '1';
}

/**
 * Safely reads HOMELAB environment variable with fallback
 */
export function getHomelabFlag(): HomelabFlag {
    const value = process.env.HOMELAB ?? '0';
    return isHomelabFlag(value) ? value : '0';
}

/**
 * Asserts that HOMELAB=1, throws if not
 * Use this at the entry point of privileged operations
 */
export function assertHomelabAccess(): void {
    const flag = getHomelabFlag();
    if (flag !== '1') {
        throw new Error(
            `Refusing operation: HOMELAB != 1 (got ${flag})\n` +
            `Set HOMELAB=1 to enable infrastructure operations on trusted machines.`
        );
    }
}

/**
 * Creates a successful command result
 */
export function success<T>(data: T): CommandResult<T> {
    return { status: 'success', data };
}

/**
 * Creates an error command result
 */
export function error<T>(error: Error, exitCode: number): CommandResult<T> {
    return { status: 'error', error, exitCode };
}

/**
 * Creates a skipped command result
 */
export function skipped<T>(reason: string): CommandResult<T> {
    return { status: 'skipped', reason };
}
