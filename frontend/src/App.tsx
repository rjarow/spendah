import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import Dashboard from './pages/Dashboard'
import Transactions from './pages/Transactions'
import Recurring from './pages/Recurring'
import Budgets from './pages/Budgets'
import Accounts from './pages/Accounts'
import AccountDetail from './pages/AccountDetail'
import Import from './pages/Import'
import Insights from './pages/Insights'
import Settings from './pages/Settings'
import NetWorth from './pages/NetWorth'
import Coach from './pages/Coach'
import Rules from './pages/Rules'
import { ErrorBoundary } from './components/ErrorBoundary'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      refetchOnWindowFocus: false,
    },
  },
})

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="transactions" element={<Transactions />} />
              <Route path="recurring" element={<Recurring />} />
              <Route path="budgets" element={<Budgets />} />
              <Route path="rules" element={<Rules />} />
              <Route path="accounts" element={<Accounts />} />
              <Route path="accounts/:id" element={<AccountDetail />} />
              <Route path="import" element={<Import />} />
              <Route path="insights" element={<Insights />} />
              <Route path="net-worth" element={<NetWorth />} />
              <Route path="settings" element={<Settings />} />
              <Route path="coach" element={<Coach />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App
