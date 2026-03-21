import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getRules,
  createRule,
  updateRule,
  deleteRule,
  testRule,
  generateRulesFromCorrections,
  createRuleFromSuggestion,
} from '@/lib/api'
import { getCategories } from '@/lib/api'
import { Button } from '@/components/ui/button'
import type { CategorizationRule, RuleCreate, RuleSuggestion, MatchField, MatchType } from '@/types'

export default function Rules() {
  const queryClient = useQueryClient()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showSuggestionsModal, setShowSuggestionsModal] = useState(false)
  const [editingRule, setEditingRule] = useState<CategorizationRule | null>(null)
  const [testText, setTestText] = useState('')
  const [testResult, setTestResult] = useState<{ matched: boolean; rule: CategorizationRule | null } | null>(null)

  const { data: rulesData, isLoading } = useQuery({
    queryKey: ['rules'],
    queryFn: () => getRules(),
  })

  const { data: categoriesData } = useQuery({
    queryKey: ['categories'],
    queryFn: () => getCategories(),
  })

  const { data: suggestionsData, isLoading: suggestionsLoading } = useQuery({
    queryKey: ['rule-suggestions'],
    queryFn: () => generateRulesFromCorrections(),
    enabled: showSuggestionsModal,
  })

  const deleteMutation = useMutation({
    mutationFn: deleteRule,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: (data: { id: string; is_active: boolean }) =>
      updateRule(data.id, { is_active: data.is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
    },
  })

  const createFromSuggestionMutation = useMutation({
    mutationFn: createRuleFromSuggestion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      queryClient.invalidateQueries({ queryKey: ['rule-suggestions'] })
    },
  })

  const handleTest = async () => {
    if (!testText.trim()) return
    const result = await testRule(testText)
    setTestResult(result)
  }

  const rules = rulesData?.items || []
  const categories = categoriesData?.items || []

  if (isLoading) {
    return <div className="p-4">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Categorization Rules</h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowSuggestionsModal(true)}>
            Generate from History
          </Button>
          <Button onClick={() => setShowCreateModal(true)}>Create Rule</Button>
        </div>
      </div>

      <div className="bg-white border rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Test Rules</h2>
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 border rounded px-3 py-2"
            placeholder="Enter merchant or description to test..."
            value={testText}
            onChange={(e) => setTestText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleTest()}
          />
          <Button onClick={handleTest}>Test</Button>
        </div>
        {testResult && (
          <div className={`mt-3 p-3 rounded ${testResult.matched ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border'}`}>
            {testResult.matched && testResult.rule ? (
              <div>
                <span className="font-medium text-green-700">Matched: </span>
                <span>{testResult.rule.name}</span>
                <span className="text-gray-500 ml-2">→ {testResult.rule.category_name}</span>
              </div>
            ) : (
              <span className="text-gray-500">No matching rule found</span>
            )}
          </div>
        )}
      </div>

      <div className="bg-white border rounded-lg overflow-hidden">
        {rules.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <p className="text-lg mb-2">No rules yet</p>
            <p className="text-sm">Create rules to auto-categorize transactions during import.</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Name</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Pattern</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Category</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Matches</th>
                <th className="text-left px-4 py-3 text-sm font-medium text-gray-500">Active</th>
                <th className="text-right px-4 py-3 text-sm font-medium text-gray-500">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rules.map((rule) => (
                <tr key={rule.id} className={!rule.is_active ? 'bg-gray-50 opacity-60' : ''}>
                  <td className="px-4 py-3">
                    <div className="font-medium">{rule.name}</div>
                    {rule.auto_created && (
                      <span className="text-xs text-gray-400">Auto-created</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded">
                      {rule.match_type}: {rule.match_value}
                    </code>
                  </td>
                  <td className="px-4 py-3">{rule.category_name}</td>
                  <td className="px-4 py-3 text-gray-500">{rule.match_count}</td>
                  <td className="px-4 py-3">
                    <button
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        rule.is_active ? 'bg-green-500' : 'bg-gray-300'
                      }`}
                      onClick={() => toggleMutation.mutate({ id: rule.id, is_active: !rule.is_active })}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          rule.is_active ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setEditingRule(rule)}
                      className="mr-2"
                    >
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (confirm('Delete this rule?')) {
                          deleteMutation.mutate(rule.id)
                        }
                      }}
                    >
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {(showCreateModal || editingRule) && (
        <RuleModal
          rule={editingRule}
          categories={categories}
          onClose={() => {
            setShowCreateModal(false)
            setEditingRule(null)
          }}
          onSave={() => {
            queryClient.invalidateQueries({ queryKey: ['rules'] })
            setShowCreateModal(false)
            setEditingRule(null)
          }}
        />
      )}

      {showSuggestionsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Suggested Rules</h2>
              <Button variant="outline" onClick={() => setShowSuggestionsModal(false)}>
                Close
              </Button>
            </div>
            {suggestionsLoading ? (
              <p>Loading suggestions...</p>
            ) : suggestionsData?.suggestions?.length === 0 ? (
              <p className="text-gray-500">No suggestions available. Make some manual categorizations first.</p>
            ) : (
              <div className="space-y-3">
                {suggestionsData?.suggestions?.map((suggestion, index) => (
                  <div key={index} className="border rounded p-4 flex justify-between items-center">
                    <div>
                      <div className="font-medium">{suggestion.name}</div>
                      <div className="text-sm text-gray-500">
                        Pattern: <code>{suggestion.match_value}</code> → {suggestion.category_name}
                      </div>
                      <div className="text-xs text-gray-400">
                        Based on {suggestion.occurrence_count} corrections
                      </div>
                    </div>
                    <Button
                      onClick={() => createFromSuggestionMutation.mutate(index)}
                      disabled={createFromSuggestionMutation.isPending}
                    >
                      Create
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function RuleModal({
  rule,
  categories,
  onClose,
  onSave,
}: {
  rule: CategorizationRule | null
  categories: { id: string; name: string }[]
  onClose: () => void
  onSave: () => void
}) {
  const [name, setName] = useState(rule?.name || '')
  const [matchField, setMatchField] = useState<MatchField>(rule?.match_field || 'merchant')
  const [matchType, setMatchType] = useState<MatchType>(rule?.match_type || 'contains')
  const [matchValue, setMatchValue] = useState(rule?.match_value || '')
  const [categoryId, setCategoryId] = useState(rule?.category_id || '')
  const [priority, setPriority] = useState(rule?.priority || 100)

  const createMutation = useMutation({
    mutationFn: (data: RuleCreate) => createRule(data),
    onSuccess: onSave,
  })

  const updateMutation = useMutation({
    mutationFn: (data: { id: string; updates: Partial<RuleCreate> }) =>
      updateRule(data.id, data.updates),
    onSuccess: onSave,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name || !matchValue || !categoryId) return

    if (rule) {
      updateMutation.mutate({
        id: rule.id,
        updates: { name, match_field: matchField, match_type: matchType, match_value: matchValue, category_id: categoryId, priority },
      })
    } else {
      createMutation.mutate({ name, match_field: matchField, match_type: matchType, match_value: matchValue, category_id: categoryId, priority })
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full">
        <h2 className="text-xl font-bold mb-4">{rule ? 'Edit Rule' : 'Create Rule'}</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Name</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Spotify → Entertainment"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Match Field</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={matchField}
                onChange={(e) => setMatchField(e.target.value as MatchField)}
              >
                <option value="merchant">Merchant</option>
                <option value="description">Description</option>
                <option value="amount">Amount</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Match Type</label>
              <select
                className="w-full border rounded px-3 py-2"
                value={matchType}
                onChange={(e) => setMatchType(e.target.value as MatchType)}
              >
                <option value="contains">Contains</option>
                <option value="exact">Exact</option>
                <option value="starts_with">Starts With</option>
                <option value="regex">Regex</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Pattern</label>
            <input
              type="text"
              className="w-full border rounded px-3 py-2"
              value={matchValue}
              onChange={(e) => setMatchValue(e.target.value)}
              placeholder="e.g., spotify"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Category</label>
            <select
              className="w-full border rounded px-3 py-2"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              required
            >
              <option value="">Select category...</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Priority</label>
            <input
              type="number"
              className="w-full border rounded px-3 py-2"
              value={priority}
              onChange={(e) => setPriority(parseInt(e.target.value) || 100)}
              min={1}
              max={1000}
            />
            <p className="text-xs text-gray-500 mt-1">Lower priority rules are checked first</p>
          </div>

          <div className="flex justify-end gap-2 pt-4">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
              {rule ? 'Update' : 'Create'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
