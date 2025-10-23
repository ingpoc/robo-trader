import React, { useState, useMemo } from 'react';
import { Order, OrderStatus, OrderFilters, OrderSortOptions } from '../types';
import { useOrderStore } from '../stores/orderStore';
import { useOrders, useCancelOrder } from '../hooks/useOrderApi';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Loader2,
  Search,
  Filter,
  SortAsc,
  SortDesc,
  Eye,
  X,
  RefreshCw,
  AlertTriangle
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { format } from 'date-fns';

interface OrderListProps {
  userId?: string;
  onOrderSelect?: (order: Order) => void;
  className?: string;
}

export const OrderList: React.FC<OrderListProps> = ({
  userId,
  onOrderSelect,
  className = '',
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const { orderFilters, orderSort, setOrderFilters, setOrderSort, applyFiltersAndSort } = useOrderStore();
  const { toast } = useToast();

  const { data: ordersData, isLoading, error, refetch } = useOrders(
    userId,
    orderFilters,
    orderSort
  );

  const cancelOrderMutation = useCancelOrder();

  // Filter orders based on search term
  const filteredOrders = useMemo(() => {
    if (!ordersData?.data) return [];

    return ordersData.data.filter(order =>
      order.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
      order.id.toLowerCase().includes(searchTerm.toLowerCase())
    );
  }, [ordersData?.data, searchTerm]);

  const handleFilterChange = (key: keyof OrderFilters, value: any) => {
    const newFilters = { ...orderFilters, [key]: value };
    // Remove empty filters
    Object.keys(newFilters).forEach(k => {
      if (newFilters[k] === '' || newFilters[k] === undefined) {
        delete newFilters[k];
      }
    });
    setOrderFilters(newFilters);
  };

  const handleSortChange = (field: OrderSortOptions['field']) => {
    const newSort: OrderSortOptions = {
      field,
      direction: orderSort.field === field && orderSort.direction === 'asc' ? 'desc' : 'asc',
    };
    setOrderSort(newSort);
  };

  const handleCancelOrder = async (orderId: string) => {
    try {
      await cancelOrderMutation.mutateAsync(orderId);
      toast({
        title: 'Order Cancelled',
        description: `Order ${orderId} has been cancelled successfully.`,
      });
    } catch (error: any) {
      toast({
        title: 'Cancellation Failed',
        description: error.message || 'Failed to cancel order.',
        variant: 'destructive',
      });
    }
  };

  const getStatusBadgeVariant = (status: OrderStatus) => {
    switch (status) {
      case 'FILLED':
        return 'default';
      case 'PARTIAL_FILL':
        return 'secondary';
      case 'PENDING':
      case 'SUBMITTED':
        return 'outline';
      case 'CANCELLED':
        return 'secondary';
      case 'REJECTED':
      case 'EXPIRED':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getStatusColor = (status: OrderStatus) => {
    switch (status) {
      case 'FILLED':
        return 'text-emerald-600';
      case 'PARTIAL_FILL':
        return 'text-copper-600';
      case 'PENDING':
      case 'SUBMITTED':
        return 'text-warmgray-600';
      case 'CANCELLED':
        return 'text-warmgray-500';
      case 'REJECTED':
      case 'EXPIRED':
        return 'text-rose-600';
      default:
        return 'text-warmgray-600';
    }
  };

  const formatPrice = (price?: number) => {
    return price ? `$${price.toFixed(2)}` : '-';
  };

  const formatQuantity = (quantity: number, filled: number) => {
    if (filled > 0) {
      return `${filled.toFixed(2)} / ${quantity.toFixed(2)}`;
    }
    return quantity.toFixed(2);
  };

  if (isLoading) {
    return (
      <Card className={`card-luxury ${className}`}>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-copper-500" />
          <span className="ml-2 text-body">Loading orders...</span>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={`card-luxury ${className}`}>
        <CardContent className="py-8">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Failed to load orders. Please try again.
            </AlertDescription>
          </Alert>
          <Button
            onClick={() => refetch()}
            variant="outline"
            className="mt-4 btn-luxury-secondary"
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={`card-luxury ${className}`}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-card-title">Orders</CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className="btn-luxury-tertiary"
            >
              <Filter className="h-4 w-4 mr-1" />
              Filters
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="btn-luxury-tertiary"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-warmgray-400" />
            <Input
              placeholder="Search orders by symbol or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-luxury pl-10"
            />
          </div>

          {showFilters && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-4 bg-warmgray-50 dark:bg-warmgray-800/50 rounded-lg">
              <Select
                value={orderFilters.side || ''}
                onValueChange={(value) => handleFilterChange('side', value || undefined)}
              >
                <SelectTrigger className="input-luxury">
                  <SelectValue placeholder="All Sides" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Sides</SelectItem>
                  <SelectItem value="BUY">Buy</SelectItem>
                  <SelectItem value="SELL">Sell</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={orderFilters.order_type || ''}
                onValueChange={(value) => handleFilterChange('order_type', value || undefined)}
              >
                <SelectTrigger className="input-luxury">
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Types</SelectItem>
                  <SelectItem value="MARKET">Market</SelectItem>
                  <SelectItem value="LIMIT">Limit</SelectItem>
                  <SelectItem value="STOP">Stop</SelectItem>
                  <SelectItem value="STOP_LIMIT">Stop Limit</SelectItem>
                  <SelectItem value="TRAILING_STOP">Trailing Stop</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={orderFilters.status || ''}
                onValueChange={(value) => handleFilterChange('status', value || undefined)}
              >
                <SelectTrigger className="input-luxury">
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Statuses</SelectItem>
                  <SelectItem value="PENDING">Pending</SelectItem>
                  <SelectItem value="SUBMITTED">Submitted</SelectItem>
                  <SelectItem value="PARTIAL_FILL">Partial Fill</SelectItem>
                  <SelectItem value="FILLED">Filled</SelectItem>
                  <SelectItem value="CANCELLED">Cancelled</SelectItem>
                  <SelectItem value="REJECTED">Rejected</SelectItem>
                  <SelectItem value="EXPIRED">Expired</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={orderFilters.time_in_force || ''}
                onValueChange={(value) => handleFilterChange('time_in_force', value || undefined)}
              >
                <SelectTrigger className="input-luxury">
                  <SelectValue placeholder="All TIF" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All TIF</SelectItem>
                  <SelectItem value="DAY">Day</SelectItem>
                  <SelectItem value="GTC">GTC</SelectItem>
                  <SelectItem value="GTD">GTD</SelectItem>
                  <SelectItem value="IOC">IOC</SelectItem>
                  <SelectItem value="FOK">FOK</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {!filteredOrders.length ? (
          <div className="text-center py-8">
            <p className="text-body-muted">No orders found matching your criteria.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="cursor-pointer hover:bg-warmgray-50 dark:hover:bg-warmgray-800/50"
                    onClick={() => handleSortChange('symbol')}
                  >
                    <div className="flex items-center gap-1">
                      Symbol
                      {orderSort.field === 'symbol' && (
                        orderSort.direction === 'asc' ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />
                      )}
                    </div>
                  </TableHead>
                  <TableHead>Side</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-warmgray-50 dark:hover:bg-warmgray-800/50"
                    onClick={() => handleSortChange('quantity')}
                  >
                    <div className="flex items-center gap-1">
                      Quantity
                      {orderSort.field === 'quantity' && (
                        orderSort.direction === 'asc' ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />
                      )}
                    </div>
                  </TableHead>
                  <TableHead>Price</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-warmgray-50 dark:hover:bg-warmgray-800/50"
                    onClick={() => handleSortChange('created_at')}
                  >
                    <div className="flex items-center gap-1">
                      Created
                      {orderSort.field === 'created_at' && (
                        orderSort.direction === 'asc' ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />
                      )}
                    </div>
                  </TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredOrders.map((order) => (
                  <TableRow key={order.id} className="hover:bg-warmgray-50 dark:hover:bg-warmgray-800/50">
                    <TableCell className="font-medium">{order.symbol}</TableCell>
                    <TableCell>
                      <Badge
                        variant={order.side === 'BUY' ? 'default' : 'secondary'}
                        className={order.side === 'BUY' ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/20 dark:text-emerald-400' : ''}
                      >
                        {order.side}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{order.order_type.replace('_', ' ')}</TableCell>
                    <TableCell>{formatQuantity(order.quantity, order.filled_quantity)}</TableCell>
                    <TableCell>{formatPrice(order.price || order.average_fill_price)}</TableCell>
                    <TableCell>
                      <Badge variant={getStatusBadgeVariant(order.status)} className={getStatusColor(order.status)}>
                        {order.status.replace('_', ' ')}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {format(new Date(order.created_at), 'MMM dd, HH:mm')}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onOrderSelect?.(order)}
                          className="h-8 w-8 p-0"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        {(order.status === 'PENDING' || order.status === 'SUBMITTED' || order.status === 'PARTIAL_FILL') && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleCancelOrder(order.id)}
                            disabled={cancelOrderMutation.isPending}
                            className="h-8 w-8 p-0 text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                          >
                            {cancelOrderMutation.isPending ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <X className="h-4 w-4" />
                            )}
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {ordersData?.pagination && ordersData.pagination.has_more && (
          <div className="flex justify-center mt-4">
            <Button variant="outline" className="btn-luxury-secondary">
              Load More
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};