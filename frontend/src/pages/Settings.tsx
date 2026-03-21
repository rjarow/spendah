import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSettings, updateAISettings, updateAPIKeys, testAIConnection, fetchProviderModels, updateTaskModels } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { PrivacySettingsPanel } from '@/components/settings/PrivacySettings'

interface Model {
  id: string
  name: string
  label: string
}

export default function Settings() {
  const queryClient = useQueryClient()
  const [testResult, setTestResult] = useState<string | null>(null)
  const [testError, setTestError] = useState<string | null>(null)
  const [apiKeyInputs, setApiKeyInputs] = useState({
    openrouter_api_key: '',
    openai_api_key: '',
    anthropic_api_key: '',
  })
  const [showKeys, setShowKeys] = useState(false)
  const [dynamicModels, setDynamicModels] = useState<Model[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [modelsError, setModelsError] = useState<string | null>(null)

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

  const updateKeysMutation = useMutation({
    mutationFn: updateAPIKeys,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      setApiKeyInputs({ openrouter_api_key: '', openai_api_key: '', anthropic_api_key: '' })
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

  const updateTaskModelsMutation = useMutation({
    mutationFn: updateTaskModels,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })

  useEffect(() => {
    if (settings?.ai?.provider) {
      handleRefreshModels(settings.ai.provider, false)
    }
  }, [settings?.ai?.provider])

  const handleRefreshModels = async (providerId: string, manual: boolean = true) => {
    setModelsLoading(true)
    setModelsError(null)
    try {
      const data = await fetchProviderModels(providerId)
      setDynamicModels(data.models)
    } catch (error: any) {
      if (manual) {
        setModelsError(error.message || 'Failed to fetch models')
      }
      const currentProvider = settings?.available_providers?.find((p: any) => p.id === providerId)
      if (currentProvider?.models) {
        setDynamicModels(currentProvider.models.map((m: string) => ({ id: m, name: m, label: m })))
      }
    } finally {
      setModelsLoading(false)
    }
  }

  if (isLoading) {
    return <div>Loading...</div>
  }

  const currentProvider = settings?.available_providers?.find(
    (p: any) => p.id === settings?.ai?.provider
  )

  const handleSaveApiKey = (provider: 'openrouter' | 'openai' | 'anthropic') => {
    const key = apiKeyInputs[`${provider}_api_key` as keyof typeof apiKeyInputs]
    if (key) {
      updateKeysMutation.mutate({ [`${provider}_api_key`]: key })
    }
  }

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
            onChange={(e) => {
              updateMutation.mutate({ provider: e.target.value })
              setDynamicModels([])
            }}
          >
            {settings?.available_providers?.map((provider: any) => (
              <option key={provider.id} value={provider.id}>
                {provider.name} {provider.requires_key ? '(API key required)' : ''}
              </option>
            ))}
          </select>
        </div>

        <div>
          <div className="flex items-center justify-between mb-1">
            <label className="block text-sm font-medium">Model</label>
            <button
              onClick={() => handleRefreshModels(settings?.ai?.provider)}
              disabled={modelsLoading}
              className="text-sm text-blue-600 hover:underline disabled:opacity-50"
            >
              {modelsLoading ? 'Loading...' : 'Refresh Models'}
            </button>
          </div>
          <select
            className="w-full border rounded p-2"
            value={settings?.ai?.model || ''}
            onChange={(e) => updateMutation.mutate({ model: e.target.value })}
          >
            {dynamicModels.length > 0 ? (
              dynamicModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.label}
                </option>
              ))
            ) : currentProvider?.models ? (
              currentProvider.models.map((model: string) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))
            ) : (
              <option value="">Select a provider first</option>
            )}
          </select>
          {modelsError && (
            <p className="text-sm text-red-600 mt-1">{modelsError}</p>
          )}
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

      <div className="border rounded-lg p-4 space-y-4">
        <h2 className="text-lg font-semibold">Per-Task Model Overrides</h2>
        <p className="text-sm text-gray-600">
          Optionally specify different models for specific AI tasks. Leave as "Use default" to use the model selected above.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Coach (Conversations)</label>
            <select
              className="w-full border rounded p-2"
              value={settings?.task_models?.coach || ''}
              onChange={(e) => updateTaskModelsMutation.mutate({ coach: e.target.value || null })}
            >
              <option value="">Use default ({settings?.ai?.model})</option>
              {dynamicModels.length > 0 ? (
                dynamicModels.map((model) => (
                  <option key={model.id} value={model.id}>{model.label}</option>
                ))
              ) : currentProvider?.models ? (
                currentProvider.models.map((model: string) => (
                  <option key={model} value={model}>{model}</option>
                ))
              ) : null}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Categorization</label>
            <select
              className="w-full border rounded p-2"
              value={settings?.task_models?.categorize || ''}
              onChange={(e) => updateTaskModelsMutation.mutate({ categorize: e.target.value || null })}
            >
              <option value="">Use default ({settings?.ai?.model})</option>
              {dynamicModels.length > 0 ? (
                dynamicModels.map((model) => (
                  <option key={model.id} value={model.id}>{model.label}</option>
                ))
              ) : currentProvider?.models ? (
                currentProvider.models.map((model: string) => (
                  <option key={model} value={model}>{model}</option>
                ))
              ) : null}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Merchant Cleaning</label>
            <select
              className="w-full border rounded p-2"
              value={settings?.task_models?.merchant_clean || ''}
              onChange={(e) => updateTaskModelsMutation.mutate({ merchant_clean: e.target.value || null })}
            >
              <option value="">Use default ({settings?.ai?.model})</option>
              {dynamicModels.length > 0 ? (
                dynamicModels.map((model) => (
                  <option key={model.id} value={model.id}>{model.label}</option>
                ))
              ) : currentProvider?.models ? (
                currentProvider.models.map((model: string) => (
                  <option key={model} value={model}>{model}</option>
                ))
              ) : null}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Format Detection</label>
            <select
              className="w-full border rounded p-2"
              value={settings?.task_models?.format_detect || ''}
              onChange={(e) => updateTaskModelsMutation.mutate({ format_detect: e.target.value || null })}
            >
              <option value="">Use default ({settings?.ai?.model})</option>
              {dynamicModels.length > 0 ? (
                dynamicModels.map((model) => (
                  <option key={model.id} value={model.id}>{model.label}</option>
                ))
              ) : currentProvider?.models ? (
                currentProvider.models.map((model: string) => (
                  <option key={model} value={model}>{model}</option>
                ))
              ) : null}
            </select>
          </div>
        </div>
      </div>

      <div className="border rounded-lg p-4 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">API Keys</h2>
          <button
            onClick={() => setShowKeys(!showKeys)}
            className="text-sm text-blue-600 hover:underline"
          >
            {showKeys ? 'Hide' : 'Show'} Keys
          </button>
        </div>
        
        <p className="text-sm text-gray-600">
          API keys are stored locally in your database and never sent to external servers except the AI provider you choose.
        </p>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">OpenRouter API Key</label>
            <div className="flex gap-2">
              <input
                type={showKeys ? 'text' : 'password'}
                className="flex-1 border rounded p-2 text-sm"
                placeholder={settings?.api_keys?.openrouter_api_key || 'Not set'}
                value={apiKeyInputs.openrouter_api_key}
                onChange={(e) => setApiKeyInputs({ ...apiKeyInputs, openrouter_api_key: e.target.value })}
              />
              <Button
                onClick={() => handleSaveApiKey('openrouter')}
                disabled={!apiKeyInputs.openrouter_api_key || updateKeysMutation.isPending}
                variant="outline"
                size="sm"
              >
                Save
              </Button>
            </div>
            {settings?.api_keys?.openrouter_api_key && (
              <p className="text-xs text-gray-500 mt-1">Current: {settings.api_keys.openrouter_api_key}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">OpenAI API Key</label>
            <div className="flex gap-2">
              <input
                type={showKeys ? 'text' : 'password'}
                className="flex-1 border rounded p-2 text-sm"
                placeholder={settings?.api_keys?.openai_api_key || 'Not set'}
                value={apiKeyInputs.openai_api_key}
                onChange={(e) => setApiKeyInputs({ ...apiKeyInputs, openai_api_key: e.target.value })}
              />
              <Button
                onClick={() => handleSaveApiKey('openai')}
                disabled={!apiKeyInputs.openai_api_key || updateKeysMutation.isPending}
                variant="outline"
                size="sm"
              >
                Save
              </Button>
            </div>
            {settings?.api_keys?.openai_api_key && (
              <p className="text-xs text-gray-500 mt-1">Current: {settings.api_keys.openai_api_key}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Anthropic API Key</label>
            <div className="flex gap-2">
              <input
                type={showKeys ? 'text' : 'password'}
                className="flex-1 border rounded p-2 text-sm"
                placeholder={settings?.api_keys?.anthropic_api_key || 'Not set'}
                value={apiKeyInputs.anthropic_api_key}
                onChange={(e) => setApiKeyInputs({ ...apiKeyInputs, anthropic_api_key: e.target.value })}
              />
              <Button
                onClick={() => handleSaveApiKey('anthropic')}
                disabled={!apiKeyInputs.anthropic_api_key || updateKeysMutation.isPending}
                variant="outline"
                size="sm"
              >
                Save
              </Button>
            </div>
            {settings?.api_keys?.anthropic_api_key && (
              <p className="text-xs text-gray-500 mt-1">Current: {settings.api_keys.anthropic_api_key}</p>
            )}
          </div>
        </div>
      </div>

      <PrivacySettingsPanel />
    </div>
  )
}
