import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketMessage {
  [key: string]: unknown;
}

interface WebSocketOptions {
  onMessage?: (data: WebSocketMessage) => void;
  onError?: (error: Event) => void;
  onClose?: () => void;
  onOpen?: () => void;
  reconnect?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

/**
 * WebSocket Hook
 *
 * 功能：
 * - 自动连接和断开
 * - 自动重连机制
 * - 消息发送和接收
 * - 连接状态管理
 */
export const useWebSocket = (url: string | null, options: WebSocketOptions = {}) => {
  const {
    onMessage,
    onError,
    onClose,
    onOpen,
    reconnect = true,
    reconnectInterval = 3000,
    maxReconnectAttempts = 5
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (!url) return;

    try {
      // 构建完整的 WebSocket URL
      // 优先使用环境变量配置的 WebSocket URL（直接连接后端）
      const wsBaseUrl = import.meta.env.VITE_WS_URL;

      console.log('[WebSocket] 环境变量 VITE_WS_URL:', wsBaseUrl);
      console.log('[WebSocket] 传入的 url:', url);

      let wsUrl: string;
      if (wsBaseUrl) {
        // 直接连接到后端（不通过 Vite 代理）
        wsUrl = url.startsWith('ws') ? url : `${wsBaseUrl}${url}`;
        console.log('[WebSocket] 使用直连模式');
      } else {
        // 通过 Vite 代理连接
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        wsUrl = url.startsWith('ws') ? url : `${protocol}//${host}${url}`;
        console.log('[WebSocket] 使用代理模式');
      }

      console.log(`[WebSocket] 最终 URL: ${wsUrl}`);
      console.log(`[WebSocket] 开始创建 WebSocket 连接...`);

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log('[WebSocket] ✅ 连接成功');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
        onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
          onMessage?.(data);
        } catch (err) {
          console.error('[WebSocket] 消息解析失败:', err);
        }
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] 连接错误:', error);
        console.error('[WebSocket] WebSocket readyState:', ws.readyState);
        console.error('[WebSocket] WebSocket url:', ws.url);
        onError?.(error);
      };

      ws.onclose = () => {
        console.log('[WebSocket] 连接关闭');
        setIsConnected(false);
        wsRef.current = null;
        onClose?.();

        // 自动重连 - 暂时禁用以便调试
        console.log('[WebSocket] 重连已禁用（调试模式）');
        /*
        if (reconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          reconnectAttemptsRef.current += 1;
          console.log(`[WebSocket] ${reconnectInterval}ms 后尝试重连 (${reconnectAttemptsRef.current}/${maxReconnectAttempts})...`);
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectInterval);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          console.warn('[WebSocket] 达到最大重连次数，停止重连');
        }
        */
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[WebSocket] 创建连接失败:', err);
    }
  }, [url, onMessage, onError, onClose, onOpen, reconnect, reconnectInterval, maxReconnectAttempts]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((data: WebSocketMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    } else {
      console.warn('[WebSocket] 连接未就绪，无法发送消息');
    }
  }, []);

  useEffect(() => {
    if (url) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [url]); // 只依赖 url，避免无限循环

  return {
    isConnected,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect: connect
  };
};
