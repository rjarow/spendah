import { useState } from 'react'
import { FileDropZone } from '@/components/imports/FileDropZone'
import { uploadFile, confirmImport, getImportHistory, getAccounts } from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { CheckCircle, FileText } from 'lucide-react'

export default function Import() {
  const queryClient = useQueryClient()
  const [uploadResponse, setUploadResponse] = useState<any>(null)
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [dateFormat, setDateFormat] = useState('%Y-%m-%d')
  const [columnMapping, setColumnMapping] = useState<any>({
    date_col: 0,
    amount_col: 1,
    description_col: 2,
  })
  const [autoCreateAccounts, setAutoCreateAccounts] = useState(false)
  const [defaultAccountType, setDefaultAccountType] = useState('checking')
  const [saveFormat, setSaveFormat] = useState(true)
  const [formatApplied, setFormatApplied] = useState(false)

  const { data: accounts } = useQuery({
    queryKey: ['accounts'],
    queryFn: getAccounts,
  })

  const { data: importHistory } = useQuery({
    queryKey: ['importHistory'],
    queryFn: getImportHistory,
  })

  const uploadMutation = useMutation({
    mutationFn: uploadFile,
    onSuccess: (data) => {
      setUploadResponse(data)
      setFormatApplied(false)

      if (data.saved_format) {
        const sf = data.saved_format
        setColumnMapping(sf.column_mapping)
        setDateFormat(sf.date_format)
        setFormatApplied(true)
        if (sf.column_mapping.account_col !== undefined) {
          setAutoCreateAccounts(true)
        }
      } else if (data.detected_format && data.detected_format.confidence > 0.5) {
        const detected = data.detected_format
        const newMapping: any = {
          date_col: detected.columns.date ?? 0,
          amount_col: detected.columns.amount ?? 1,
          description_col: detected.columns.description ?? 2,
        }
        
        if (detected.columns.debit !== null && detected.columns.debit !== undefined) {
          newMapping.debit_col = detected.columns.debit
        }
        if (detected.columns.credit !== null && detected.columns.credit !== undefined) {
          newMapping.credit_col = detected.columns.credit
        }
        if (detected.columns.balance !== null && detected.columns.balance !== undefined) {
          newMapping.balance_col = detected.columns.balance
        }
        if (detected.columns.account !== null && detected.columns.account !== undefined) {
          newMapping.account_col = detected.columns.account
          setAutoCreateAccounts(true)
        }
        
        setColumnMapping(newMapping)
        
        if (detected.date_format) {
          const formatMap: Record<string, string> = {
            '%Y-%m-%d': '%Y-%m-%d',
            '%m/%d/%Y': '%m/%d/%Y',
            '%d/%m/%Y': '%d/%m/%Y',
            '%m-%d-%Y': '%m-%d-%Y',
          }
          setDateFormat(formatMap[detected.date_format] || '%Y-%m-%d')
        }
      }
    },
  })

  const confirmMutation = useMutation({
    mutationFn: ({ importId, data }: { importId: string; data: any }) =>
      confirmImport(importId, data),
    onSuccess: () => {
      setUploadResponse(null)
      setFormatApplied(false)
      queryClient.invalidateQueries({ queryKey: ['importHistory'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['accounts'] })
    },
  })

  const handleFileSelect = (file: File) => {
    uploadMutation.mutate(file)
  }

  const handleConfirm = () => {
    if (!uploadResponse) return
    if (!autoCreateAccounts && !selectedAccount) return

    const data: any = {
      column_mapping: columnMapping,
      date_format: dateFormat,
      save_format: saveFormat,
    }

    if (autoCreateAccounts && columnMapping.account_col !== undefined) {
      data.auto_create_accounts = true
      data.default_account_type = defaultAccountType
    } else {
      data.account_id = selectedAccount
    }

    confirmMutation.mutate({
      importId: uploadResponse.import_id,
      data,
    })
  }

  const hasAccountColumn = columnMapping.account_col !== undefined && columnMapping.account_col !== null
  const canImport = autoCreateAccounts && hasAccountColumn ? true : !!selectedAccount

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Import Transactions</h1>

      {!uploadResponse ? (
        <FileDropZone
          onFileSelect={handleFileSelect}
          isUploading={uploadMutation.isPending}
        />
      ) : (
        <div className="space-y-4 p-4 border rounded-lg">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Confirm Import</h2>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <FileText className="w-4 h-4" />
              {uploadResponse.filename} ({uploadResponse.row_count} rows)
            </div>
          </div>

          {uploadResponse.saved_format && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-medium text-green-800">
                    Matched saved format: {uploadResponse.saved_format.name}
                  </div>
                  <div className="text-sm text-green-700 mt-1">
                    Column mapping auto-applied from previous import
                    {uploadResponse.saved_format.account_name && ` for ${uploadResponse.saved_format.account_name}`}
                  </div>
                </div>
              </div>
            </div>
          )}

          {!uploadResponse.saved_format && uploadResponse.detected_format && uploadResponse.detected_format.confidence > 0.5 && (
            <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-800">
              AI detected format: {uploadResponse.detected_format.source_guess || 'Unknown source'}
              {' '}({Math.round(uploadResponse.detected_format.confidence * 100)}% confidence)
              {hasAccountColumn && (
                <span className="block mt-1">
                  Multiple accounts detected - will auto-create accounts from CSV
                </span>
              )}
            </div>
          )}

          {hasAccountColumn && (
            <div className="bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-800">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoCreateAccounts}
                  onChange={(e) => setAutoCreateAccounts(e.target.checked)}
                  className="rounded"
                />
                <span>Auto-create accounts from CSV (Account column detected)</span>
              </label>
              {autoCreateAccounts && (
                <div className="mt-2">
                  <label className="block text-sm font-medium mb-1">Default Account Type</label>
                  <select
                    className="border rounded p-1 text-sm"
                    value={defaultAccountType}
                    onChange={(e) => setDefaultAccountType(e.target.value)}
                  >
                    <option value="checking">Checking</option>
                    <option value="savings">Savings</option>
                    <option value="credit_card">Credit Card</option>
                  </select>
                </div>
              )}
            </div>
          )}

          {(!hasAccountColumn || !autoCreateAccounts) && (
            <div>
              <label className="block text-sm font-medium mb-1">Account</label>
              <select
                className="w-full border rounded p-2"
                value={selectedAccount}
                onChange={(e) => setSelectedAccount(e.target.value)}
              >
                <option value="">Select account...</option>
                {accounts?.items?.map((acc: any) => (
                  <option key={acc.id} value={acc.id}>
                    {acc.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Date Column</label>
              <select
                className="w-full border rounded p-2"
                value={columnMapping.date_col}
                onChange={(e) =>
                  setColumnMapping({ ...columnMapping, date_col: parseInt(e.target.value) })
                }
              >
                {uploadResponse.headers.map((h: string, i: number) => (
                  <option key={i} value={i}>
                    {h}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Amount Column</label>
              <select
                className="w-full border rounded p-2"
                value={columnMapping.amount_col}
                onChange={(e) =>
                  setColumnMapping({ ...columnMapping, amount_col: parseInt(e.target.value) })
                }
              >
                {uploadResponse.headers.map((h: string, i: number) => (
                  <option key={i} value={i}>
                    {h}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description Column</label>
              <select
                className="w-full border rounded p-2"
                value={columnMapping.description_col}
                onChange={(e) =>
                  setColumnMapping({ ...columnMapping, description_col: parseInt(e.target.value) })
                }
              >
                {uploadResponse.headers.map((h: string, i: number) => (
                  <option key={i} value={i}>
                    {h}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {hasAccountColumn && (
            <div>
              <label className="block text-sm font-medium mb-1">Account Column</label>
              <select
                className="w-full border rounded p-2"
                value={columnMapping.account_col ?? ''}
                onChange={(e) =>
                  setColumnMapping({ 
                    ...columnMapping, 
                    account_col: e.target.value ? parseInt(e.target.value) : undefined 
                  })
                }
              >
                <option value="">None</option>
                {uploadResponse.headers.map((h: string, i: number) => (
                  <option key={i} value={i}>
                    {h}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">Date Format</label>
            <select
              className="w-full border rounded p-2"
              value={dateFormat}
              onChange={(e) => setDateFormat(e.target.value)}
            >
              <option value="%Y-%m-%d">YYYY-MM-DD</option>
              <option value="%m/%d/%Y">MM/DD/YYYY</option>
              <option value="%d/%m/%Y">DD/MM/YYYY</option>
              <option value="%m-%d-%Y">MM-DD-YYYY</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Preview</label>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm border">
                <thead>
                  <tr className="bg-gray-50">
                    {uploadResponse.headers.map((h: string, i: number) => (
                      <th key={i} className="px-2 py-1 border text-left">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {uploadResponse.preview_rows.map((row: string[], i: number) => (
                    <tr key={i}>
                      {row.map((cell: string, j: number) => (
                        <td key={j} className="px-2 py-1 border">
                          {cell}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="bg-gray-50 border rounded p-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={saveFormat}
                onChange={(e) => setSaveFormat(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm">
                Remember this format for future imports
                {!uploadResponse.saved_format && selectedAccount && accounts?.items && (
                  <span className="text-gray-500">
                    {' '}(for {accounts.items.find((a: any) => a.id === selectedAccount)?.name || 'this account'})
                  </span>
                )}
              </span>
            </label>
          </div>

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setUploadResponse(null)
                setFormatApplied(false)
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={!canImport || confirmMutation.isPending}
            >
              {confirmMutation.isPending
                ? 'Importing...'
                : `Import ${uploadResponse.row_count} Transactions`}
            </Button>
          </div>

          {confirmMutation.isSuccess && (
            <div className="bg-green-50 border border-green-200 rounded p-3 text-green-800">
              Import successful! Your transactions have been imported.
            </div>
          )}
          {confirmMutation.isError && (
            <div className="bg-red-50 border border-red-200 rounded p-3 text-red-800">
              Import failed. Please try again.
            </div>
          )}
        </div>
      )}

      <div>
        <h2 className="text-lg font-semibold mb-2">Recent Imports</h2>
        {importHistory && importHistory.length > 0 ? (
          <div className="space-y-2">
            {importHistory.map((log: any) => (
              <div
                key={log.id}
                className="p-3 border rounded flex justify-between items-center"
              >
                <div>
                  <p className="font-medium">{log.filename}</p>
                  <p className="text-sm text-gray-500">
                    {new Date(log.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="text-right">
                  <p
                    className={`text-sm ${
                      log.status === 'completed'
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}
                  >
                    {log.status}
                  </p>
                  <p className="text-sm text-gray-500">
                    {log.transactions_imported} imported, {log.transactions_skipped}{' '}
                    skipped
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No imports yet</p>
        )}
      </div>
    </div>
  )
}
