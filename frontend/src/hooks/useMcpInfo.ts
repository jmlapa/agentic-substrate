import { useQuery } from '@tanstack/react-query';
import { mcpApi, McpInfoResponse } from '../api/mcp-api';

export const useMcpInfo = () => {
  return useQuery<McpInfoResponse>({
    queryKey: ['mcp-info'],
    queryFn: mcpApi.getInfo,
    refetchInterval: 10000,
    retry: 2,
  });
};
