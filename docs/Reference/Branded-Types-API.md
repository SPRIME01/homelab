# Branded Types API

Branded types live in `packages/homelab-types/src/index.ts` and enforce compile-time safety when handling security-sensitive strings.

## Type Aliases

| Type | Description |
| --- | --- |
| `TailscaleIP` | IPv4 address in the 100.64.0.0/10 range used by Tailscale |
| `TailscaleMachineID` | Stable machine identifier assigned by Tailscale |
| `SOPSFilePath` | File path ending with `.sops` |
| `AgeRecipient` | Public key string beginning with `age1` followed by 58 base58 chars |
| `AgeIdentityPath` | Filesystem path to an age identity file |
| `NxProjectName` | Lowercase alphanumeric string with hyphens (max 63 characters) |
| `NxTargetName` | Lowercase alphanumeric/hyphen/colon string (max 63 characters) |
| `NxAgentToken` | String used to authenticate Nx agents |
| `HomelabFlag` | `'0'` or `'1'` |
| `CommandResult<T>` | Discriminated union for success/error/skipped outcomes |

## Helper Functions

| Function | Purpose |
| --- | --- |
| `isTailscaleIP(value)` / `createTailscaleIP(raw)` | Validate or construct a `TailscaleIP`; throws on invalid format |
| `isAgeRecipient(value)` / `createAgeRecipient(raw)` | Validate age recipients |
| `isSOPSFilePath(value)` / `createSOPSFilePath(raw)` | Ensure file paths end with `.sops` |
| `isNxProjectName(value)` / `createNxProjectName(raw)` | Validate Nx project naming conventions |
| `isNxTargetName(value)` / `createNxTargetName(raw)` | Validate Nx target names |
| `isHomelabFlag(value)` / `getHomelabFlag()` / `assertHomelabAccess()` | Guard runtime entry points |
| `success(data)`, `error(error, exitCode)`, `skipped(reason)` | Produce typed `CommandResult` objects |

## Usage Example

```typescript
import {
  createTailscaleIP,
  assertHomelabAccess,
  success,
  error,
  skipped,
} from '@homelab/homelab-types';

export function connect(host: string) {
  assertHomelabAccess();
  try {
    const ip = createTailscaleIP(host);
    // run ssh command with ip
    return success({ ip });
  } catch (err) {
    if (!process.env.TAILSCALE_AUTHKEY) {
      return skipped('tailscale auth key missing');
    }
    return error(err as Error, 1);
  }
}
```

Use these APIs inside Pulumi programs, Ansible helper scripts, and Nx tooling to prevent mixing arbitrary strings with sensitive identifiers.
