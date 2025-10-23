import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  RiskLimit,
  StopLossTemplate,
  RebalancingRule,
  EmergencyOverride,
  RiskMonitoringStatus,
  PortfolioRiskMetrics
} from '../types';

interface RiskStoreState {
  // Risk Limits
  riskLimits: RiskLimit[];
  selectedLimit: RiskLimit | null;

  // Stop-Loss Templates
  stopLossTemplates: StopLossTemplate[];
  selectedTemplate: StopLossTemplate | null;

  // Rebalancing Rules
  rebalancingRules: RebalancingRule[];
  selectedRule: RebalancingRule | null;

  // Emergency Overrides
  emergencyOverrides: EmergencyOverride[];
  activeOverride: EmergencyOverride | null;

  // Real-time Monitoring
  monitoringStatus: RiskMonitoringStatus | null;
  riskMetrics: PortfolioRiskMetrics | null;

  // UI State
  isLoading: boolean;
  error: string | null;
  activeTab: 'limits' | 'stop-loss' | 'rebalancing' | 'alerts' | 'metrics' | 'overrides';

  // Actions
  setRiskLimits: (limits: RiskLimit[]) => void;
  setSelectedLimit: (limit: RiskLimit | null) => void;
  updateRiskLimit: (limitId: string, updates: Partial<RiskLimit>) => void;
  addRiskLimit: (limit: RiskLimit) => void;
  removeRiskLimit: (limitId: string) => void;

  setStopLossTemplates: (templates: StopLossTemplate[]) => void;
  setSelectedTemplate: (template: StopLossTemplate | null) => void;
  updateStopLossTemplate: (templateId: string, updates: Partial<StopLossTemplate>) => void;
  addStopLossTemplate: (template: StopLossTemplate) => void;
  removeStopLossTemplate: (templateId: string) => void;

  setRebalancingRules: (rules: RebalancingRule[]) => void;
  setSelectedRule: (rule: RebalancingRule | null) => void;
  updateRebalancingRule: (ruleId: string, updates: Partial<RebalancingRule>) => void;
  addRebalancingRule: (rule: RebalancingRule) => void;
  removeRebalancingRule: (ruleId: string) => void;

  setEmergencyOverrides: (overrides: EmergencyOverride[]) => void;
  setActiveOverride: (override: EmergencyOverride | null) => void;
  addEmergencyOverride: (override: EmergencyOverride) => void;
  deactivateOverride: (overrideId: string) => void;

  setMonitoringStatus: (status: RiskMonitoringStatus | null) => void;
  setRiskMetrics: (metrics: PortfolioRiskMetrics | null) => void;

  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setActiveTab: (tab: RiskStoreState['activeTab']) => void;

  // Reset
  reset: () => void;
}

const initialState = {
  riskLimits: [],
  selectedLimit: null,
  stopLossTemplates: [],
  selectedTemplate: null,
  rebalancingRules: [],
  selectedRule: null,
  emergencyOverrides: [],
  activeOverride: null,
  monitoringStatus: null,
  riskMetrics: null,
  isLoading: false,
  error: null,
  activeTab: 'limits' as const,
};

export const useRiskStore = create<RiskStoreState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      // Risk Limits Actions
      setRiskLimits: (limits) => set({ riskLimits: limits }),
      setSelectedLimit: (limit) => set({ selectedLimit: limit }),
      updateRiskLimit: (limitId, updates) =>
        set((state) => ({
          riskLimits: state.riskLimits.map(limit =>
            limit.id === limitId ? { ...limit, ...updates } : limit
          ),
          selectedLimit: state.selectedLimit?.id === limitId
            ? { ...state.selectedLimit, ...updates }
            : state.selectedLimit
        })),
      addRiskLimit: (limit) =>
        set((state) => ({ riskLimits: [...state.riskLimits, limit] })),
      removeRiskLimit: (limitId) =>
        set((state) => ({
          riskLimits: state.riskLimits.filter(limit => limit.id !== limitId),
          selectedLimit: state.selectedLimit?.id === limitId ? null : state.selectedLimit
        })),

      // Stop-Loss Templates Actions
      setStopLossTemplates: (templates) => set({ stopLossTemplates: templates }),
      setSelectedTemplate: (template) => set({ selectedTemplate: template }),
      updateStopLossTemplate: (templateId, updates) =>
        set((state) => ({
          stopLossTemplates: state.stopLossTemplates.map(template =>
            template.id === templateId ? { ...template, ...updates } : template
          ),
          selectedTemplate: state.selectedTemplate?.id === templateId
            ? { ...state.selectedTemplate, ...updates }
            : state.selectedTemplate
        })),
      addStopLossTemplate: (template) =>
        set((state) => ({ stopLossTemplates: [...state.stopLossTemplates, template] })),
      removeStopLossTemplate: (templateId) =>
        set((state) => ({
          stopLossTemplates: state.stopLossTemplates.filter(template => template.id !== templateId),
          selectedTemplate: state.selectedTemplate?.id === templateId ? null : state.selectedTemplate
        })),

      // Rebalancing Rules Actions
      setRebalancingRules: (rules) => set({ rebalancingRules: rules }),
      setSelectedRule: (rule) => set({ selectedRule: rule }),
      updateRebalancingRule: (ruleId, updates) =>
        set((state) => ({
          rebalancingRules: state.rebalancingRules.map(rule =>
            rule.id === ruleId ? { ...rule, ...updates } : rule
          ),
          selectedRule: state.selectedRule?.id === ruleId
            ? { ...state.selectedRule, ...updates }
            : state.selectedRule
        })),
      addRebalancingRule: (rule) =>
        set((state) => ({ rebalancingRules: [...state.rebalancingRules, rule] })),
      removeRebalancingRule: (ruleId) =>
        set((state) => ({
          rebalancingRules: state.rebalancingRules.filter(rule => rule.id !== ruleId),
          selectedRule: state.selectedRule?.id === ruleId ? null : state.selectedRule
        })),

      // Emergency Overrides Actions
      setEmergencyOverrides: (overrides) => set({ emergencyOverrides: overrides }),
      setActiveOverride: (override) => set({ activeOverride: override }),
      addEmergencyOverride: (override) =>
        set((state) => ({ emergencyOverrides: [...state.emergencyOverrides, override] })),
      deactivateOverride: (overrideId) =>
        set((state) => ({
          emergencyOverrides: state.emergencyOverrides.map(override =>
            override.id === overrideId ? { ...override, is_active: false } : override
          ),
          activeOverride: state.activeOverride?.id === overrideId ? null : state.activeOverride
        })),

      // Monitoring Actions
      setMonitoringStatus: (status) => set({ monitoringStatus: status }),
      setRiskMetrics: (metrics) => set({ riskMetrics: metrics }),

      // UI Actions
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error }),
      setActiveTab: (activeTab) => set({ activeTab }),

      // Reset
      reset: () => set(initialState),
    }),
    {
      name: 'risk-store',
    }
  )
);