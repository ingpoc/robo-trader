import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useConfig } from '@/hooks/useConfig'

export function Config() {
  const { config: serverConfig, isLoading, updateConfig, isUpdating } = useConfig()
  const [localConfig, setLocalConfig] = useState({
    maxTurns: '5',
    riskTolerance: '5',
    dailyApiLimit: '25',
  })

  // Load config from server when available
  useEffect(() => {
    if (serverConfig) {
      setLocalConfig({
        maxTurns: String(serverConfig.max_turns || 5),
        riskTolerance: String(serverConfig.risk_tolerance || 5),
        dailyApiLimit: String(serverConfig.daily_api_limit || 25),
      })
    }
  }, [serverConfig])

  const handleSave = () => {
    const configToSave = {
      max_turns: parseInt(localConfig.maxTurns),
      risk_tolerance: parseInt(localConfig.riskTolerance),
      daily_api_limit: parseInt(localConfig.dailyApiLimit),
    }
    updateConfig(configToSave)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-lg text-gray-600">Loading configuration...</div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6 p-6 overflow-auto max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Settings</h1>
        <p className="text-sm text-gray-600">Configure system parameters</p>
      </div>

      <div className="flex flex-col gap-4 p-4 bg-white border border-gray-200 rounded">
        <div>
          <label htmlFor="maxTurns" className="block text-sm font-medium text-gray-700 mb-1">
            Max Conversation Turns
          </label>
          <Input
            id="maxTurns"
            type="number"
            value={localConfig.maxTurns}
            onChange={(e) => setLocalConfig({ ...localConfig, maxTurns: e.target.value })}
          />
        </div>

        <div>
          <label htmlFor="riskTolerance" className="block text-sm font-medium text-gray-700 mb-1">
            Risk Tolerance (1-10)
          </label>
          <Input
            id="riskTolerance"
            type="number"
            min="1"
            max="10"
            value={localConfig.riskTolerance}
            onChange={(e) => setLocalConfig({ ...localConfig, riskTolerance: e.target.value })}
          />
        </div>

        <div>
          <label htmlFor="dailyApiLimit" className="block text-sm font-medium text-gray-700 mb-1">
            Daily API Call Limit
          </label>
          <Input
            id="dailyApiLimit"
            type="number"
            value={localConfig.dailyApiLimit}
            onChange={(e) => setLocalConfig({ ...localConfig, dailyApiLimit: e.target.value })}
          />
        </div>

        <Button onClick={handleSave} disabled={isUpdating}>
          {isUpdating ? 'Saving...' : 'Save Configuration'}
        </Button>
      </div>
    </div>
  )
}
