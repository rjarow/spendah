import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import AlertBell from '@/components/alerts/AlertBell'

export default function Layout() {
  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <div className="flex-1 overflow-y-auto">
        <div className="container mx-auto p-8 flex justify-between items-start">
          <div className="flex-1">
            <Outlet />
          </div>
          <AlertBell />
        </div>
      </div>
    </div>
  )
}
