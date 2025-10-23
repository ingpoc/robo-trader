import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  Order,
  OrderTemplate,
  OrderGroup,
  BracketOrder,
  OrderMonitoringStatus,
  OrderFilters,
  OrderSortOptions,
  OrderStatistics,
  ConditionalOrder,
  OrderFormData,
  OrderTemplateFormData,
  BracketOrderFormData,
  OrderGroupFormData,
} from '../types';

interface OrderStoreState {
  // Orders
  orders: Order[];
  selectedOrder: Order | null;
  filteredOrders: Order[];
  orderFilters: OrderFilters;
  orderSort: OrderSortOptions;

  // Order Templates
  orderTemplates: OrderTemplate[];
  selectedTemplate: OrderTemplate | null;

  // Order Groups and Baskets
  orderGroups: OrderGroup[];
  selectedGroup: OrderGroup | null;

  // Bracket Orders
  bracketOrders: BracketOrder[];
  selectedBracket: BracketOrder | null;

  // Conditional Orders
  conditionalOrders: ConditionalOrder[];
  selectedConditional: ConditionalOrder | null;

  // Real-time Monitoring
  monitoringStatus: OrderMonitoringStatus | null;
  orderStatistics: OrderStatistics | null;

  // UI State
  isLoading: boolean;
  error: string | null;
  activeTab: 'orders' | 'templates' | 'groups' | 'brackets' | 'monitoring' | 'history';

  // Form State
  orderFormData: OrderFormData | null;
  templateFormData: OrderTemplateFormData | null;
  bracketFormData: BracketOrderFormData | null;
  groupFormData: OrderGroupFormData | null;

  // Actions - Orders
  setOrders: (orders: Order[]) => void;
  setSelectedOrder: (order: Order | null) => void;
  addOrder: (order: Order) => void;
  updateOrder: (orderId: string, updates: Partial<Order>) => void;
  removeOrder: (orderId: string) => void;
  setOrderFilters: (filters: OrderFilters) => void;
  setOrderSort: (sort: OrderSortOptions) => void;
  applyFiltersAndSort: () => void;

  // Actions - Templates
  setOrderTemplates: (templates: OrderTemplate[]) => void;
  setSelectedTemplate: (template: OrderTemplate | null) => void;
  addOrderTemplate: (template: OrderTemplate) => void;
  updateOrderTemplate: (templateId: string, updates: Partial<OrderTemplate>) => void;
  removeOrderTemplate: (templateId: string) => void;

  // Actions - Groups
  setOrderGroups: (groups: OrderGroup[]) => void;
  setSelectedGroup: (group: OrderGroup | null) => void;
  addOrderGroup: (group: OrderGroup) => void;
  updateOrderGroup: (groupId: string, updates: Partial<OrderGroup>) => void;
  removeOrderGroup: (groupId: string) => void;

  // Actions - Brackets
  setBracketOrders: (brackets: BracketOrder[]) => void;
  setSelectedBracket: (bracket: BracketOrder | null) => void;
  addBracketOrder: (bracket: BracketOrder) => void;
  updateBracketOrder: (bracketId: string, updates: Partial<BracketOrder>) => void;
  removeBracketOrder: (bracketId: string) => void;

  // Actions - Conditional Orders
  setConditionalOrders: (orders: ConditionalOrder[]) => void;
  setSelectedConditional: (order: ConditionalOrder | null) => void;
  addConditionalOrder: (order: ConditionalOrder) => void;
  updateConditionalOrder: (orderId: string, updates: Partial<ConditionalOrder>) => void;
  removeConditionalOrder: (orderId: string) => void;

  // Actions - Monitoring
  setMonitoringStatus: (status: OrderMonitoringStatus | null) => void;
  setOrderStatistics: (stats: OrderStatistics | null) => void;

  // Actions - Forms
  setOrderFormData: (data: OrderFormData | null) => void;
  setTemplateFormData: (data: OrderTemplateFormData | null) => void;
  setBracketFormData: (data: BracketOrderFormData | null) => void;
  setGroupFormData: (data: OrderGroupFormData | null) => void;

  // Actions - UI
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setActiveTab: (tab: OrderStoreState['activeTab']) => void;

  // Utility Actions
  reset: () => void;
  clearSelections: () => void;
}

const initialState = {
  orders: [],
  selectedOrder: null,
  filteredOrders: [],
  orderFilters: {},
  orderSort: { field: 'created_at', direction: 'desc' },

  orderTemplates: [],
  selectedTemplate: null,

  orderGroups: [],
  selectedGroup: null,

  bracketOrders: [],
  selectedBracket: null,

  conditionalOrders: [],
  selectedConditional: null,

  monitoringStatus: null,
  orderStatistics: null,

  isLoading: false,
  error: null,
  activeTab: 'orders' as const,

  orderFormData: null,
  templateFormData: null,
  bracketFormData: null,
  groupFormData: null,
};

export const useOrderStore = create<OrderStoreState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Orders Actions
      setOrders: (orders) => set({ orders }, false, 'setOrders'),
      setSelectedOrder: (order) => set({ selectedOrder: order }, false, 'setSelectedOrder'),
      addOrder: (order) =>
        set((state) => ({ orders: [...state.orders, order] }), false, 'addOrder'),
      updateOrder: (orderId, updates) =>
        set((state) => ({
          orders: state.orders.map(order =>
            order.id === orderId ? { ...order, ...updates } : order
          ),
          selectedOrder: state.selectedOrder?.id === orderId
            ? { ...state.selectedOrder, ...updates }
            : state.selectedOrder
        }), false, 'updateOrder'),
      removeOrder: (orderId) =>
        set((state) => ({
          orders: state.orders.filter(order => order.id !== orderId),
          selectedOrder: state.selectedOrder?.id === orderId ? null : state.selectedOrder
        }), false, 'removeOrder'),
      setOrderFilters: (filters) =>
        set({ orderFilters: filters }, false, 'setOrderFilters'),
      setOrderSort: (sort) =>
        set({ orderSort: sort }, false, 'setOrderSort'),
      applyFiltersAndSort: () => {
        const { orders, orderFilters, orderSort } = get();

        let filtered = [...orders];

        // Apply filters
        if (orderFilters.symbol) {
          filtered = filtered.filter(order =>
            order.symbol.toLowerCase().includes(orderFilters.symbol!.toLowerCase())
          );
        }
        if (orderFilters.side) {
          filtered = filtered.filter(order => order.side === orderFilters.side);
        }
        if (orderFilters.order_type) {
          filtered = filtered.filter(order => order.order_type === orderFilters.order_type);
        }
        if (orderFilters.status) {
          filtered = filtered.filter(order => order.status === orderFilters.status);
        }
        if (orderFilters.time_in_force) {
          filtered = filtered.filter(order => order.time_in_force === orderFilters.time_in_force);
        }
        if (orderFilters.date_from) {
          filtered = filtered.filter(order =>
            new Date(order.created_at) >= new Date(orderFilters.date_from!)
          );
        }
        if (orderFilters.date_to) {
          filtered = filtered.filter(order =>
            new Date(order.created_at) <= new Date(orderFilters.date_to!)
          );
        }
        if (orderFilters.tags && orderFilters.tags.length > 0) {
          filtered = filtered.filter(order =>
            orderFilters.tags!.some(tag => order.tags?.includes(tag))
          );
        }

        // Apply sorting
        filtered.sort((a, b) => {
          const aValue = a[orderSort.field];
          const bValue = b[orderSort.field];

          let comparison = 0;
          if (aValue < bValue) comparison = -1;
          if (aValue > bValue) comparison = 1;

          return orderSort.direction === 'desc' ? -comparison : comparison;
        });

        set({ filteredOrders: filtered }, false, 'applyFiltersAndSort');
      },

      // Templates Actions
      setOrderTemplates: (templates) => set({ orderTemplates: templates }, false, 'setOrderTemplates'),
      setSelectedTemplate: (template) => set({ selectedTemplate: template }, false, 'setSelectedTemplate'),
      addOrderTemplate: (template) =>
        set((state) => ({ orderTemplates: [...state.orderTemplates, template] }), false, 'addOrderTemplate'),
      updateOrderTemplate: (templateId, updates) =>
        set((state) => ({
          orderTemplates: state.orderTemplates.map(template =>
            template.id === templateId ? { ...template, ...updates } : template
          ),
          selectedTemplate: state.selectedTemplate?.id === templateId
            ? { ...state.selectedTemplate, ...updates }
            : state.selectedTemplate
        }), false, 'updateOrderTemplate'),
      removeOrderTemplate: (templateId) =>
        set((state) => ({
          orderTemplates: state.orderTemplates.filter(template => template.id !== templateId),
          selectedTemplate: state.selectedTemplate?.id === templateId ? null : state.selectedTemplate
        }), false, 'removeOrderTemplate'),

      // Groups Actions
      setOrderGroups: (groups) => set({ orderGroups: groups }, false, 'setOrderGroups'),
      setSelectedGroup: (group) => set({ selectedGroup: group }, false, 'setSelectedGroup'),
      addOrderGroup: (group) =>
        set((state) => ({ orderGroups: [...state.orderGroups, group] }), false, 'addOrderGroup'),
      updateOrderGroup: (groupId, updates) =>
        set((state) => ({
          orderGroups: state.orderGroups.map(group =>
            group.id === groupId ? { ...group, ...updates } : group
          ),
          selectedGroup: state.selectedGroup?.id === groupId
            ? { ...state.selectedGroup, ...updates }
            : state.selectedGroup
        }), false, 'updateOrderGroup'),
      removeOrderGroup: (groupId) =>
        set((state) => ({
          orderGroups: state.orderGroups.filter(group => group.id !== groupId),
          selectedGroup: state.selectedGroup?.id === groupId ? null : state.selectedGroup
        }), false, 'removeOrderGroup'),

      // Bracket Orders Actions
      setBracketOrders: (brackets) => set({ bracketOrders: brackets }, false, 'setBracketOrders'),
      setSelectedBracket: (bracket) => set({ selectedBracket: bracket }, false, 'setSelectedBracket'),
      addBracketOrder: (bracket) =>
        set((state) => ({ bracketOrders: [...state.bracketOrders, bracket] }), false, 'addBracketOrder'),
      updateBracketOrder: (bracketId, updates) =>
        set((state) => ({
          bracketOrders: state.bracketOrders.map(bracket =>
            bracket.id === bracketId ? { ...bracket, ...updates } : bracket
          ),
          selectedBracket: state.selectedBracket?.id === bracketId
            ? { ...state.selectedBracket, ...updates }
            : state.selectedBracket
        }), false, 'updateBracketOrder'),
      removeBracketOrder: (bracketId) =>
        set((state) => ({
          bracketOrders: state.bracketOrders.filter(bracket => bracket.id !== bracketId),
          selectedBracket: state.selectedBracket?.id === bracketId ? null : state.selectedBracket
        }), false, 'removeBracketOrder'),

      // Conditional Orders Actions
      setConditionalOrders: (orders) => set({ conditionalOrders: orders }, false, 'setConditionalOrders'),
      setSelectedConditional: (order) => set({ selectedConditional: order }, false, 'setSelectedConditional'),
      addConditionalOrder: (order) =>
        set((state) => ({ conditionalOrders: [...state.conditionalOrders, order] }), false, 'addConditionalOrder'),
      updateConditionalOrder: (orderId, updates) =>
        set((state) => ({
          conditionalOrders: state.conditionalOrders.map(order =>
            order.id === orderId ? { ...order, ...updates } : order
          ),
          selectedConditional: state.selectedConditional?.id === orderId
            ? { ...state.selectedConditional, ...updates }
            : state.selectedConditional
        }), false, 'updateConditionalOrder'),
      removeConditionalOrder: (orderId) =>
        set((state) => ({
          conditionalOrders: state.conditionalOrders.filter(order => order.id !== orderId),
          selectedConditional: state.selectedConditional?.id === orderId ? null : state.selectedConditional
        }), false, 'removeConditionalOrder'),

      // Monitoring Actions
      setMonitoringStatus: (status) => set({ monitoringStatus: status }, false, 'setMonitoringStatus'),
      setOrderStatistics: (stats) => set({ orderStatistics: stats }, false, 'setOrderStatistics'),

      // Form Actions
      setOrderFormData: (data) => set({ orderFormData: data }, false, 'setOrderFormData'),
      setTemplateFormData: (data) => set({ templateFormData: data }, false, 'setTemplateFormData'),
      setBracketFormData: (data) => set({ bracketFormData: data }, false, 'setBracketFormData'),
      setGroupFormData: (data) => set({ groupFormData: data }, false, 'setGroupFormData'),

      // UI Actions
      setLoading: (loading) => set({ isLoading: loading }, false, 'setLoading'),
      setError: (error) => set({ error }, false, 'setError'),
      setActiveTab: (activeTab) => set({ activeTab }, false, 'setActiveTab'),

      // Utility Actions
      reset: () => set(initialState, false, 'reset'),
      clearSelections: () =>
        set({
          selectedOrder: null,
          selectedTemplate: null,
          selectedGroup: null,
          selectedBracket: null,
          selectedConditional: null,
        }, false, 'clearSelections'),
    }),
    {
      name: 'order-store',
    }
  )
);