import { useEffect, useRef, useCallback } from 'react';
import { useRiskStore } from '../stores/riskStore';
import { RiskWebSocketEvent, RiskMonitoringStatus, PortfolioRiskMetrics, RiskAlert } from '../types';

const WS_URL = 'ws://localhost:8000/ws/monitor';

export const useRiskWebSocket = (token?: string) => {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000; // 3 seconds

  const {
    setMonitoringStatus,
    setRiskMetrics,
    setEmergencyOverrides,
    setActiveOverride,
  } = useRiskStore();

  const connect = useCallback(() => {
    if (!token) return;

    try {
      const wsUrl = `${WS_URL}?token=${token}`;
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('Risk WebSocket connected');
        reconnectAttempts.current = 0;
      };

      wsRef.current.onmessage = (event) => {
        try {
          const data: RiskWebSocketEvent = JSON.parse(event.data);

          switch (data.type) {
            case 'risk_alert':
              // Handle risk alert - could trigger notifications
              console.log('Risk alert received:', data.data);
              // Update alerts in store if needed
              break;

            case 'stop_loss_triggered':
              console.log('Stop-loss triggered:', data.data);
              // Could trigger UI updates or notifications
              break;

            case 'risk_metrics_update':
              const metrics: PortfolioRiskMetrics = data.data;
              setRiskMetrics(metrics);
              break;

            case 'limit_breach':
              console.log('Risk limit breached:', data.data);
              // Handle limit breach notifications
              break;

            default:
              console.log('Unknown WebSocket event:', data.type);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log('Risk WebSocket disconnected:', event.code, event.reason);

        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          reconnectAttempts.current++;
          console.log(`Attempting to reconnect (${reconnectAttempts.current}/${maxReconnectAttempts})...`);

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        }
      };

      wsRef.current.onerror = (error) => {
        console.error('Risk WebSocket error:', error);
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
    }
  }, [token, setRiskMetrics]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounting');
      wsRef.current = null;
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }, []);

  // Subscribe to specific risk monitoring updates
  const subscribeToPortfolio = useCallback((portfolioId: string) => {
    sendMessage({
      type: 'subscribe',
      data: { portfolio_id: portfolioId }
    });
  }, [sendMessage]);

  const unsubscribeFromPortfolio = useCallback((portfolioId: string) => {
    sendMessage({
      type: 'unsubscribe',
      data: { portfolio_id: portfolioId }
    });
  }, [sendMessage]);

  // Request real-time monitoring status
  const requestMonitoringStatus = useCallback(() => {
    sendMessage({
      type: 'request_status',
      data: {}
    });
  }, [sendMessage]);

  useEffect(() => {
    if (token) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [token, connect, disconnect]);

  // Connection status
  const isConnected = wsRef.current?.readyState === WebSocket.OPEN;
  const isConnecting = wsRef.current?.readyState === WebSocket.CONNECTING;
  const connectionState = wsRef.current?.readyState;

  return {
    isConnected,
    isConnecting,
    connectionState,
    sendMessage,
    subscribeToPortfolio,
    unsubscribeFromPortfolio,
    requestMonitoringStatus,
    reconnect: connect,
    disconnect,
  };
};

// Hook for monitoring specific portfolio risk metrics
export const usePortfolioRiskMonitoring = (portfolioId: string, token?: string) => {
  const { subscribeToPortfolio, unsubscribeFromPortfolio, isConnected } = useRiskWebSocket(token);
  const { riskMetrics } = useRiskStore();

  useEffect(() => {
    if (isConnected && portfolioId) {
      subscribeToPortfolio(portfolioId);
    }

    return () => {
      if (portfolioId) {
        unsubscribeFromPortfolio(portfolioId);
      }
    };
  }, [portfolioId, isConnected, subscribeToPortfolio, unsubscribeFromPortfolio]);

  return {
    riskMetrics,
    isConnected,
  };
};

// Hook for real-time risk alerts
export const useRiskAlertsRealtime = (token?: string) => {
  const { isConnected } = useRiskWebSocket(token);
  const alertsRef = useRef<RiskAlert[]>([]);

  // This would integrate with a notification system
  const handleAlert = useCallback((alert: RiskAlert) => {
    alertsRef.current.push(alert);

    // Trigger browser notification if permission granted
    if (Notification.permission === 'granted') {
      new Notification(`Risk Alert: ${alert.title}`, {
        body: alert.message,
        icon: '/risk-alert-icon.png',
        tag: `risk-alert-${alert.id}`,
      });
    }

    // Could also trigger toast notifications, sound alerts, etc.
  }, []);

  return {
    isConnected,
    alerts: alertsRef.current,
    handleAlert,
  };
};