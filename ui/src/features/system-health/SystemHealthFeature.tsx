/**
 * System Health Feature
 * Monitors backend systems, schedulers, queues, and infrastructure
 */

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Breadcrumb } from '@/components/common/Breadcrumb'
import { Activity, Database, Radio, Cpu, AlertCircle } from 'lucide-react'
import { useSystemHealth } from './hooks/useSystemHealth'
import { SchedulerStatus } from './components/SchedulerStatus'
import { QueueHealthMonitor } from './components/QueueHealthMonitor'
import { DatabaseStatus } from './components/DatabaseStatus'
import { ResourceUsage } from './components/ResourceUsage'
import { ErrorAlerts } from './components/ErrorAlerts'

export const SystemHealthFeature: React.FC = () => {
  const { schedulerStatus, queueHealth, dbHealth, resources, errors, isLoading } = useSystemHealth()

  return (
    <div className="page-wrapper">
      <div className="flex flex-col gap-4 animate-fade-in-luxury">
        <Breadcrumb />

        {/* Header */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-950 rounded-lg">
              <Activity className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-4xl lg:text-5xl font-bold text-warmgray-900 dark:text-warmgray-100 font-serif">
                System Health
              </h1>
              <p className="text-lg text-warmgray-600 dark:text-warmgray-400 mt-2">
                Monitor backend systems, schedulers, and infrastructure
              </p>
            </div>
          </div>
        </div>

        {/* Quick Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className={schedulerStatus?.healthy ? 'border-l-4 border-l-emerald-500' : 'border-l-4 border-l-red-500'}>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Activity className="w-5 h-5" />
                Schedulers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{schedulerStatus?.healthy ? 'Healthy' : 'Error'}</p>
              <p className="text-sm text-warmgray-600 mt-1">Last run: {schedulerStatus?.lastRun}</p>
            </CardContent>
          </Card>

          <Card className={queueHealth?.healthy ? 'border-l-4 border-l-emerald-500' : 'border-l-4 border-l-red-500'}>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Radio className="w-5 h-5" />
                Queues
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{queueHealth?.totalTasks || 0}</p>
              <p className="text-sm text-warmgray-600 mt-1">Total tasks queued</p>
            </CardContent>
          </Card>

          <Card className={dbHealth?.healthy ? 'border-l-4 border-l-emerald-500' : 'border-l-4 border-l-red-500'}>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <Database className="w-5 h-5" />
                Database
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{dbHealth?.healthy ? 'Connected' : 'Error'}</p>
              <p className="text-sm text-warmgray-600 mt-1">Connections: {dbHealth?.activeConnections || 0}</p>
            </CardContent>
          </Card>

          <Card className={errors && errors.length === 0 ? 'border-l-4 border-l-emerald-500' : 'border-l-4 border-l-amber-500'}>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2">
                <AlertCircle className="w-5 h-5" />
                Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">{errors?.length || 0}</p>
              <p className="text-sm text-warmgray-600 mt-1">Recent errors</p>
            </CardContent>
          </Card>
        </div>

        {/* Detailed Tabs */}
        <Tabs defaultValue="schedulers" className="w-full">
          <TabsList className="grid w-full grid-cols-5 mb-6 p-1.5 bg-warmgray-100 dark:bg-warmgray-800 rounded-lg border border-warmgray-300 dark:border-warmgray-700 shadow-sm">
            <TabsTrigger value="schedulers" className="text-sm font-semibold rounded-md">
              Schedulers
            </TabsTrigger>
            <TabsTrigger value="queues" className="text-sm font-semibold rounded-md">
              Queues
            </TabsTrigger>
            <TabsTrigger value="database" className="text-sm font-semibold rounded-md">
              Database
            </TabsTrigger>
            <TabsTrigger value="resources" className="text-sm font-semibold rounded-md">
              Resources
            </TabsTrigger>
            <TabsTrigger value="errors" className="text-sm font-semibold rounded-md">
              Errors
            </TabsTrigger>
          </TabsList>

          <TabsContent value="schedulers" className="space-y-4">
            <SchedulerStatus status={schedulerStatus} isLoading={isLoading} />
          </TabsContent>

          <TabsContent value="queues" className="space-y-4">
            <QueueHealthMonitor health={queueHealth} isLoading={isLoading} />
          </TabsContent>

          <TabsContent value="database" className="space-y-4">
            <DatabaseStatus health={dbHealth} isLoading={isLoading} />
          </TabsContent>

          <TabsContent value="resources" className="space-y-4">
            <ResourceUsage resources={resources} isLoading={isLoading} />
          </TabsContent>

          <TabsContent value="errors" className="space-y-4">
            <ErrorAlerts errors={errors} isLoading={isLoading} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default SystemHealthFeature
