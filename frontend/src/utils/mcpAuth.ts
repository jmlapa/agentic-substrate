/**
 * Utilitários para autenticação HTTP Basic compatível com RFC 7617 e Caddy Reverse Proxy.
 */

/**
 * Codifica credenciais no formato Base64 seguro para UTF-8.
 */
export function encodeBasicAuth(username: string, password: string): string {
  if (!username && !password) return '';
  const combined = `${username}:${password}`;
  // Codificação segura para UTF-8 no ambiente de browser e Node.js/Vitest
  if (typeof window !== 'undefined' && typeof window.btoa === 'function') {
    return window.btoa(unescape(encodeURIComponent(combined)));
  }
  return Buffer.from(combined, 'utf-8').toString('base64');
}

/**
 * Monta o valor do cabeçalho HTTP Authorization (RFC 7617).
 */
export function buildBasicAuthHeader(
  username: string,
  password: string
): string | null {
  if (!username) return null;
  const token = encodeBasicAuth(username, password);
  return `Basic ${token}`;
}

/**
 * Retorna o mapa de cabeçalhos de autenticação para clientes MCP.
 */
export function buildMcpHeaders(
  username: string,
  password: string
): Record<string, string> | undefined {
  const header = buildBasicAuthHeader(username, password);
  if (!header) return undefined;
  return {
    Authorization: header,
  };
}
