import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateAISettings, testAIConnection } from '@/lib/api'
import { Button } from '@/components/ui/button'

export default function Settings() {
  const queryClient = useQueryClient()
  const [testResult, setTestResult] = useState<string | null>(null)
  const [testError, setTestError] = useState<string | null>(null)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: getSettings,
  })

  const updateMutation = useMutation({
    mutationFn: updateAISettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })

  const testMutation = useMutation({
    mutationFn: testAIConnection,
    onSuccess: (data) => {
      setTestResult(data.response)
      setTestError(null)
    },
    onError: (error: any) => {
      setTestError(error.response?.data?.detail || 'Connection failed')
      setTestResult(null)
    },
  })

  if (isLoading) {
    return <div>Loading...</div>
  }

  const currentProvider = settings?.available_providers?.find(
    (p: any) => p.id === settings?.ai?.provider
  )

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      <div className="border rounded-lg p-4 space-y-4">
        <h2 className="text-lg font-semibold">AI Configuration</h2>

        <div>
          <label className="block text-sm font-medium mb-1">AI Provider</label>
          <select
            className="w-full border rounded p-2"
            value={settings?.ai?.provider || ''}
            onChange={(e) => updateMutation.mutate({ provider: e.target.value })}
          >
            {settings?.available_providers?.map((provider: any) => (
              <option key={provider.id} value={provider.id}>
                {provider.name} {provider.requires_key ? '(API key required)' : ''}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Model</label>
          <select
            className="w-full border rounded p-2"
            value={settings?.ai?.model || ''}
            onChange={(e) => updateMutation.mutate({ model: e.target.value })}
          >
            {currentProvider?.models?.map((model: string) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings?.ai?.auto_categorize ?? true}
              onChange={(e) => updateMutation.mutate({ auto_categorize: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm">Auto-categorize transactions</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings?.ai?.clean_merchants ?? true}
              onChange={(e) => updateMutation.mutate({ clean_merchants: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm">Clean merchant names</span>
          </label>

          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={settings?.ai?.detect_format ?? true}
              onChange={(e) => updateMutation.mutate({ detect_format: e.target.checked })}
              className="rounded"
            />
            <span className="text-sm">AI format detection for CSV files</span>
          </label>
        </div>

        <div className="pt-4 border-t">
          <Button
            onClick={() => testMutation.mutate()}
            disabled={testMutation.isPending}
            variant="outline"
          >
            {testMutation.isPending ? 'Testing...' : 'Test AI Connection'}
          </Button>

          {testResult && (
            <p className="mt-2 text-sm text-green-600">
              ✓ Connection successful: {testResult}
            </p>
          )}

          {testError && (
            <p className="mt-2 text-sm text-red-600">
              ✗ {testError}
            </p>
          )}
        </div>
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded p-4 text-sm">
        <p className="font-medium text-yellow-800">API Key Configuration</p>
        <p className="text-yellow-700 mt-1">
          API keys are configured via environment variables for security.
          Set <code className="bg-yellow-100 px-1">OPENROUTER_API_KEY</code>,
          <code className="bg-yellow-100 px-1">ANTHROPIC_API_KEY</code>, or
          <code className="bg-yellow-100 px-1">OPENAI_API_KEY</code> in your
          <code className="bg-yellow-100 px-1">.env</code> file.
        </p>
      </div>
    </div>
  )
}
