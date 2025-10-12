import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { useConfig } from '@/hooks/useConfig'
import { SkeletonLoader } from '@/components/common/SkeletonLoader'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { Settings, Save, RotateCcw } from 'lucide-react'

export function Config() {
  const { config: serverConfig, isLoading, updateConfig, isUpdating } = useConfig()
  const [localConfig, setLocalConfig] = useState({
    maxTurns: '5',
    riskTolerance: '5',
    dailyApiLimit: '25',
  })
  const [hasChanges, setHasChanges] = useState(false)

  // Load config from server when available
  useEffect(() => {
    if (serverConfig) {
      const newConfig = {
        maxTurns: String(serverConfig.max_turns || 5),
        riskTolerance: String(serverConfig.risk_tolerance || 5),
        dailyApiLimit: String(serverConfig.daily_api_limit || 25),
      }
      setLocalConfig(newConfig)
      setHasChanges(false)
    }
  }, [serverConfig])

  // Check for changes
  useEffect(() => {
    if (serverConfig) {
      const changed = (
        localConfig.maxTurns !== String(serverConfig.max_turns || 5) ||
        localConfig.riskTolerance !== String(serverConfig.risk_tolerance || 5) ||
        localConfig.dailyApiLimit !== String(serverConfig.daily_api_limit || 25)
      )
      setHasChanges(changed)
    }
  }, [localConfig, serverConfig])

  const handleSave = () => {
    const configToSave = {
      max_turns: parseInt(localConfig.maxTurns),
      risk_tolerance: parseInt(localConfig.riskTolerance),
      daily_api_limit: parseInt(localConfig.dailyApiLimit),
    }
    updateConfig(configToSave)
  }

  const handleReset = () => {
    if (serverConfig) {
      setLocalConfig({
        maxTurns: String(serverConfig.max_turns || 5),
        riskTolerance: String(serverConfig.risk_tolerance || 5),
        dailyApiLimit: String(serverConfig.daily_api_limit || 25),
      })
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 p-4 lg:p-6 animate-fade-in">
        <Breadcrumb />
        <div className="flex flex-col gap-4">
          <SkeletonLoader className="h-8 w-48" />
          <SkeletonLoader className="h-4 w-64" />
        </div>
        <Card className="max-w-2xl">
          <CardHeader>
            <SkeletonLoader className="h-6 w-32" />
          </CardHeader>
          <CardContent className="space-y-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="space-y-2">
                <SkeletonLoader className="h-4 w-24" />
                <SkeletonLoader className="h-10 w-full" />
              </div>
            ))}
            <SkeletonLoader className="h-10 w-32" />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6 overflow-auto">
      <div className="flex flex-col gap-4">
        <Breadcrumb />
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-lg text-gray-600 mt-1">Configure system parameters and preferences</p>
        </div>
      </div>

      <Card className="max-w-2xl shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-blue-600" />
            System Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <label htmlFor="maxTurns" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Max Conversation Turns
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Maximum number of conversation turns allowed per session
            </p>
            <Input
              id="maxTurns"
              type="number"
              min="1"
              max="50"
              value={localConfig.maxTurns}
              onChange={(e) => setLocalConfig({ ...localConfig, maxTurns: e.target.value })}
              className="max-w-xs"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="riskTolerance" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Risk Tolerance (1-10)
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Higher values allow more aggressive trading strategies
            </p>
            <Input
              id="riskTolerance"
              type="number"
              min="1"
              max="10"
              value={localConfig.riskTolerance}
              onChange={(e) => setLocalConfig({ ...localConfig, riskTolerance: e.target.value })}
              className="max-w-xs"
            />
          </div>

          <div className="space-y-2">
            <label htmlFor="dailyApiLimit" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
              Daily API Call Limit
            </label>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Maximum number of API calls allowed per day
            </p>
            <Input
              id="dailyApiLimit"
              type="number"
              min="1"
              value={localConfig.dailyApiLimit}
              onChange={(e) => setLocalConfig({ ...localConfig, dailyApiLimit: e.target.value })}
              className="max-w-xs"
            />
          </div>

          <div className="flex gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
            <Button
              onClick={handleSave}
              disabled={isUpdating || !hasChanges}
              className="flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              {isUpdating ? 'Saving...' : 'Save Changes'}
            </Button>
            <Button
              variant="outline"
              onClick={handleReset}
              disabled={!hasChanges}
              className="flex items-center gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Reset
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}