import { describe, it, expect } from 'vitest';
import {
  encodeBasicAuth,
  buildBasicAuthHeader,
  buildMcpHeaders,
} from '../src/utils/mcpAuth';

describe('MCP Basic Auth Utilities (RFC 7617 & Caddy Compatibility)', () => {
  it('correctly encodes standard ASCII credentials to base64', () => {
    // admin:secret -> Base64 is 'YWRtaW46c2VjcmV0'
    const token = encodeBasicAuth('admin', 'secret');
    expect(token).toBe('YWRtaW46c2VjcmV0');
  });

  it('correctly builds standard Authorization header string', () => {
    const header = buildBasicAuthHeader('admin', 'secret');
    expect(header).toBe('Basic YWRtaW46c2VjcmV0');
  });

  it('handles empty credentials gracefully', () => {
    expect(encodeBasicAuth('', '')).toBe('');
    expect(buildBasicAuthHeader('', '')).toBeNull();
    expect(buildMcpHeaders('', '')).toBeUndefined();
  });

  it('generates headers dictionary for MCP client configurations', () => {
    const headers = buildMcpHeaders('developer', 'p@ssw0rd!');
    expect(headers).toBeDefined();
    expect(headers).toHaveProperty('Authorization');
    expect(headers?.Authorization.startsWith('Basic ')).toBe(true);
  });
});
