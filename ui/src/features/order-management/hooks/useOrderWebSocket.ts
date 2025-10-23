import { useEffect, useRef } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { OrderWebSocketEvent, Order, OrderExecution, OrderStatusChange } from '../types';
import { useOrderStore } from '../stores/orderStore';

export const useOrderWebSocket = (userId?: string) => {
  const { connectionStatus, subscribe, unsubscribe } = useWebSocket();
  const subscriptionRef = useRef<string | null>(null);
  const {
    addOrder,
    updateOrder,
    setMonitoringStatus,
    setOrderStatistics,
  } = useOrderStore();

  useEffect(() => {
    if (!userId || connectionStatus !== 'connected') return;

    // Subscribe to order events
    const subscriptionId = subscribe<OrderWebSocketEvent>(
      `orders:${userId}`,
      (event: OrderWebSocketEvent) => {
        handleOrderEvent(event);
      }
    );

    subscriptionRef.current = subscriptionId;

    // Cleanup on unmount or dependency change
    return () => {
      if (subscriptionRef.current) {
        unsubscribe(subscriptionRef.current);
        subscriptionRef.current = null;
      }
    };
  }, [userId, connectionStatus, subscribe, unsubscribe]);

  const handleOrderEvent = (event: OrderWebSocketEvent) => {
    switch (event.type) {
      case 'order_created':
        handleOrderCreated(event.data as Order);
        break;
      case 'order_updated':
        handleOrderUpdated(event.data as Order);
        break;
      case 'order_executed':
        handleOrderExecuted(event.data as OrderExecution);
        break;
      case 'order_cancelled':
        handleOrderCancelled(event.data as Order);
        break;
      case 'order_rejected':
        handleOrderRejected(event.data as Order);
        break;
      default:
        console.warn('Unknown order event type:', event.type);
    }
  };

  const handleOrderCreated = (order: Order) => {
    addOrder(order);
    // Could trigger a toast notification here
    console.log('Order created:', order.id);
  };

  const handleOrderUpdated = (order: Order) => {
    updateOrder(order.id, order);
    // Update monitoring status if needed
    if (order.status === 'FILLED' || order.status === 'CANCELLED') {
      // Refresh monitoring data
      setMonitoringStatus(null); // This will trigger a refetch
    }
  };

  const handleOrderExecuted = (execution: OrderExecution) => {
    // Update order with execution data
    // This would typically involve updating the order's filled quantity and average price
    console.log('Order executed:', execution);
    // Refresh monitoring status
    setMonitoringStatus(null);
    setOrderStatistics(null);
  };

  const handleOrderCancelled = (order: Order) => {
    updateOrder(order.id, { status: 'CANCELLED' });
    console.log('Order cancelled:', order.id);
    // Refresh monitoring status
    setMonitoringStatus(null);
  };

  const handleOrderRejected = (order: Order) => {
    updateOrder(order.id, { status: 'REJECTED' });
    console.log('Order rejected:', order.id);
    // Could trigger an error notification
  };

  return {
    isConnected: connectionStatus === 'connected',
    connectionStatus,
  };
};

// Hook for real-time order monitoring
export const useOrderMonitoringWebSocket = (userId?: string) => {
  const { connectionStatus, subscribe, unsubscribe } = useWebSocket();
  const subscriptionRef = useRef<string | null>(null);
  const { setMonitoringStatus, setOrderStatistics } = useOrderStore();

  useEffect(() => {
    if (!userId || connectionStatus !== 'connected') return;

    // Subscribe to monitoring events
    const subscriptionId = subscribe(
      `order-monitoring:${userId}`,
      (event: any) => {
        if (event.type === 'monitoring_update') {
          setMonitoringStatus(event.data);
        } else if (event.type === 'statistics_update') {
          setOrderStatistics(event.data);
        }
      }
    );

    subscriptionRef.current = subscriptionId;

    return () => {
      if (subscriptionRef.current) {
        unsubscribe(subscriptionRef.current);
        subscriptionRef.current = null;
      }
    };
  }, [userId, connectionStatus, subscribe, unsubscribe, setMonitoringStatus, setOrderStatistics]);

  return {
    isConnected: connectionStatus === 'connected',
    connectionStatus,
  };
};

// Hook for order execution feed
export const useOrderExecutionFeed = (userId?: string, symbol?: string) => {
  const { connectionStatus, subscribe, unsubscribe } = useWebSocket();
  const subscriptionRef = useRef<string | null>(null);
  const executionsRef = useRef<OrderExecution[]>([]);

  useEffect(() => {
    if (!userId || connectionStatus !== 'connected') return;

    const channel = symbol ? `executions:${userId}:${symbol}` : `executions:${userId}`;

    const subscriptionId = subscribe<OrderExecution>(
      channel,
      (execution: OrderExecution) => {
        executionsRef.current = [execution, ...executionsRef.current.slice(0, 99)]; // Keep last 100
      }
    );

    subscriptionRef.current = subscriptionId;

    return () => {
      if (subscriptionRef.current) {
        unsubscribe(subscriptionRef.current);
        subscriptionRef.current = null;
      }
    };
  }, [userId, symbol, connectionStatus, subscribe, unsubscribe]);

  return {
    executions: executionsRef.current,
    isConnected: connectionStatus === 'connected',
    connectionStatus,
  };
};