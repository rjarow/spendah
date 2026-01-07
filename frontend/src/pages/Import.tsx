import { useState } from 'react'
import { FileDropZone } from '@/components/imports/FileDropZone'
import { uploadFile, confirmImport, getImportHistory, getAccounts } from '@/lib/api'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'

export default function Import() {
  const queryClient = useQueryClient()
  const [uploadResponse, setUploadResponse] = useState<any>(null)
  const [selectedAccount, setSelectedAccount] = useState<string>('')
  const [dateFormat, setDateFormat] = useState('%Y-%m-%d')
  const [columnMapping, setColumnMapping] = useState({
    date_col: 0,
    amount_col: 1,
    description_col: 2,
  })

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

      if (data.detected_format && data.detected_format.confidence > 0.5) {
        const detected = data.detected_format
        setColumnMapping({
          date_col: detected.columns.date ?? 0,
          amount_col: detected.columns.amount ?? 1,
          description_col: detected.columns.description ?? 2,
        })
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
      queryClient.invalidateQueries({ queryKey: ['importHistory'] })
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
    },
  })

  const handleFileSelect = (file: File) => {
    uploadMutation.mutate(file)
  }

  const handleConfirm = () => {
    if (!uploadResponse || !selectedAccount) return

    confirmMutation.mutate({
      importId: uploadResponse.import_id,
      data: {
        account_id: selectedAccount,
        column_mapping: columnMapping,
        date_format: dateFormat,
      },
    })
  }

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
          <h2 className="text-lg font-semibold">Confirm Import</h2>
          <p className="text-sm text-gray-600">
            File: {uploadResponse.filename} ({uploadResponse.row_count} rows)
          </p>

          {uploadResponse.detected_format && uploadResponse.detected_format.confidence > 0.5 && (
            <div className="bg-green-50 border border-green-200 rounded p-3 text-sm text-green-800 mb-4">
              ✨ AI detected format: {uploadResponse.detected_format.source_guess || 'Unknown source'}
              {' '}({Math.round(uploadResponse.detected_format.confidence * 100)}% confidence)
            </div>
          )}

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

          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => setUploadResponse(null)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={!selectedAccount || confirmMutation.isPending}
            >
              {confirmMutation.isPending
                ? 'Importing...'
                : `Import ${uploadResponse.row_count} Transactions`}
            </Button>
          </div>

          {confirmMutation.isSuccess && (
            <p className="text-green-600">Import successful!</p>
          )}
          {confirmMutation.isError && (
            <p className="text-red-600">Import failed. Please try again.</p>
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
