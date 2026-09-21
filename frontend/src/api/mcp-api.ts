import { apiClient } from './client';

export interface McpToolParameter {
  name: string;
  type: string;
  required: boolean;
  description: string;
}

export interface McpToolInfo {
  name: string;
  description: string;
  category: string;
  parameters: McpToolParameter[];
}

export interface McpInfoResponse {
  status: string;
  version: string;
  transport: string;
  sse_endpoint: string;
  messages_endpoint: string;
  tools: McpToolInfo[];
}

export const mcpApi = {
  async getInfo(): Promise<McpInfoResponse> {
    const response = await apiClient.get<McpInfoResponse>('/api/v1/mcp/info');
    return response.data;
  },
};
