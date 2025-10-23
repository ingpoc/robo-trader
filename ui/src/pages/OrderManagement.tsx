import React, { useState } from 'react';
import { Order } from '../features/order-management/types';
import {
  OrderForm,
  OrderList,
  OrderTemplateManager,
  BracketOrderCreator,
  OrderManagementDashboard
} from '../features/order-management/components';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/Dialog';
import {
  Plus,
  List,
  FileText,
  Target,
  BarChart3,
  Settings
} from 'lucide-react';

const OrderManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [showOrderForm, setShowOrderForm] = useState(false);
  const [showBracketCreator, setShowBracketCreator] = useState(false);

  const handleOrderSelect = (order: Order) => {
    setSelectedOrder(order);
    setActiveTab('orders');
  };

  const handleOrderCreated = () => {
    setShowOrderForm(false);
    setShowBracketCreator(false);
    setActiveTab('orders');
  };

  const handleTemplateApplied = () => {
    setActiveTab('orders');
  };

  return (
    <div className="page-wrapper">
      <div className="page-header">
        <div>
          <h1 className="page-title">Order Management</h1>
          <p className="page-subtitle">
            Create, monitor, and manage your trading orders with advanced order types and templates
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => setShowOrderForm(true)}
            className="btn-luxury-primary"
          >
            <Plus className="mr-2 h-4 w-4" />
            New Order
          </Button>
  
          <Button
            onClick={() => setShowBracketCreator(true)}
            variant="outline"
            className="btn-luxury-secondary"
          >
            <Target className="mr-2 h-4 w-4" />
            Bracket Order
          </Button>
  
          <Dialog open={showOrderForm} onOpenChange={setShowOrderForm}>
            <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Create New Order</DialogTitle>
              </DialogHeader>
              <OrderForm
                onSuccess={handleOrderCreated}
                onCancel={() => setShowOrderForm(false)}
              />
            </DialogContent>
          </Dialog>
  
          <Dialog open={showBracketCreator} onOpenChange={setShowBracketCreator}>
            <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>Create Bracket Order</DialogTitle>
              </DialogHeader>
              <BracketOrderCreator
                onSuccess={handleOrderCreated}
                onCancel={() => setShowBracketCreator(false)}
              />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="dashboard" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Dashboard
          </TabsTrigger>
          <TabsTrigger value="orders" className="flex items-center gap-2">
            <List className="h-4 w-4" />
            Orders
          </TabsTrigger>
          <TabsTrigger value="templates" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Templates
          </TabsTrigger>
          <TabsTrigger value="brackets" className="flex items-center gap-2">
            <Target className="h-4 w-4" />
            Brackets
          </TabsTrigger>
          <TabsTrigger value="settings" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard" className="space-y-6">
          <OrderManagementDashboard />
        </TabsContent>

        <TabsContent value="orders" className="space-y-6">
          <OrderList
            onOrderSelect={handleOrderSelect}
          />

          {selectedOrder && (
            <Card className="card-luxury">
              <CardHeader>
                <CardTitle className="text-card-title">Order Details</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm font-medium text-body-muted">Order ID</label>
                      <p className="text-body font-mono">{selectedOrder.id}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-body-muted">Symbol</label>
                      <p className="text-body">{selectedOrder.symbol}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-body-muted">Side</label>
                      <p className="text-body">{selectedOrder.side}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-body-muted">Type</label>
                      <p className="text-body">{selectedOrder.order_type}</p>
                    </div>
                  </div>
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm font-medium text-body-muted">Quantity</label>
                      <p className="text-body">{selectedOrder.quantity}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-body-muted">Price</label>
                      <p className="text-body">${selectedOrder.price || 'Market'}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-body-muted">Status</label>
                      <p className="text-body">{selectedOrder.status}</p>
                    </div>
                    <div>
                      <label className="text-sm font-medium text-body-muted">Time in Force</label>
                      <p className="text-body">{selectedOrder.time_in_force}</p>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="templates" className="space-y-6">
          <OrderTemplateManager
            onApplyTemplate={handleTemplateApplied}
          />
        </TabsContent>

        <TabsContent value="brackets" className="space-y-6">
          <Card className="card-luxury">
            <CardHeader>
              <CardTitle className="text-card-title">Bracket Orders</CardTitle>
              <p className="text-body-muted">
                One-click orders with entry, stop loss, and take profit levels
              </p>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12">
                <Target className="h-16 w-16 text-copper-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">Bracket Order Management</h3>
                <p className="text-body-muted mb-6">
                  View and manage your bracket orders with automated risk management.
                </p>
                <Button
                  onClick={() => setShowBracketCreator(true)}
                  className="btn-luxury-primary"
                >
                  <Target className="mr-2 h-4 w-4" />
                  Create Bracket Order
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="space-y-6">
          <Card className="card-luxury">
            <CardHeader>
              <CardTitle className="text-card-title">Order Management Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div>
                  <h4 className="text-sm font-semibold mb-3">Default Settings</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-body-muted">Default Time in Force</label>
                      <p className="text-body">DAY</p>
                    </div>
                    <div>
                      <label className="text-sm text-body-muted">Default Order Type</label>
                      <p className="text-body">MARKET</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-semibold mb-3">Risk Management</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-body-muted">Max Order Value</label>
                      <p className="text-body">$100,000</p>
                    </div>
                    <div>
                      <label className="text-sm text-body-muted">Default Stop Loss %</label>
                      <p className="text-body">5%</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-semibold mb-3">Notifications</h4>
                  <div className="space-y-2">
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" defaultChecked className="rounded" />
                      <span className="text-sm">Order execution notifications</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" defaultChecked className="rounded" />
                      <span className="text-sm">Order status updates</span>
                    </label>
                    <label className="flex items-center space-x-2">
                      <input type="checkbox" className="rounded" />
                      <span className="text-sm">Risk limit warnings</span>
                    </label>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default OrderManagement;