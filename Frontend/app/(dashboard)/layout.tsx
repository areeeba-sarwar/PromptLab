import { AuthProvider } from '@/contexts/auth-context'
import { Sidebar } from '@/components/dashboard/sidebar'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthProvider>
      <div className="min-h-screen bg-background">
        <Sidebar />
        <main className="lg:pl-64">
          <div className="min-h-screen">
            {children}
          </div>
        </main>
      </div>
    </AuthProvider>
  )
}
