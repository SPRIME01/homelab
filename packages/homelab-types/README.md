# @homelab/types

Branded TypeScript types for security-sensitive values in homelab infrastructure.

## Purpose

This library provides compile-time type safety for strings that represent security-critical values:
- Tailscale IP addresses
- SOPS encrypted file paths
- Age encryption keys
- Nx project and target names
- Environment flags

By using branded types, we prevent accidental mixing of different string types (e.g., passing a plain string where a Tailscale IP is expected).

## Usage

```typescript
import {
  TailscaleIP,
  createTailscaleIP,
  assertHomelabAccess,
  success,
  error,
  skipped
} from '@homelab/types';

// Validate at runtime, get type safety at compile time
const agentIP: TailscaleIP = createTailscaleIP('100.64.0.10');

// Guard privileged operations
assertHomelabAccess(); // Throws if HOMELAB !== '1'

// Use discriminated unions for command results
function deployInfra(): CommandResult<string> {
  try {
    assertHomelabAccess();
    // ... deploy logic
    return success('Deployment complete');
  } catch (err) {
    return error(err as Error, 1);
  }
}
```

## Type Guards

All branded types include type guards for runtime validation:

- `isTailscaleIP(value)` - Validates 100.x.x.x range
- `isAgeRecipient(value)` - Validates age1... format
- `isSOPSFilePath(value)` - Validates .sops extension
- `isNxProjectName(value)` - Validates Nx naming conventions
- `isHomelabFlag(value)` - Validates '0' or '1'

## Defense in Depth

These types are part of the homelab security model:
1. Environment detection (HOMELAB flag)
2. Type safety (branded types, this library)
3. Runtime validation (type guards)
4. Explicit confirmation (DEPLOY_CONFIRM)
5. Network isolation (REQUIRE_TAILSCALE)

See `docs/Security Philosophy` in copilot-instructions.md for full threat model.
