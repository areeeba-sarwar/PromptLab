'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  BookOpen,
  Zap,
  Sparkles,
  LayoutDashboard,
  LogOut,
  Menu,
  X
} from 'lucide-react'
import { PromptLabIcon } from '@/components/promptlab-logo'
import { Button } from '@/components/ui/button'
import { ThemeToggle } from '@/components/theme-toggle'
import { useState } from 'react'
import { useAuth } from '@/contexts/auth-context'

const navItems = [
  {
    title: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard
  },
  {
    title: 'Learning',
    href: '/dashboard/learning',
    icon: BookOpen
  },
  {
    title: 'Live Evaluation',
    href: '/dashboard/evaluation',
    icon: Zap
  },
  {
    title: 'Prompt Enhancer',
    href: '/dashboard/enhancer',
    icon: Sparkles
  }
]

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { logout } = useAuth()
  const [isMobileOpen, setIsMobileOpen] = useState(false)

  const handleLogout = () => {
    logout()
    router.push('/sign-in')
  }

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-4 left-4 z-50 lg:hidden text-foreground"
        onClick={() => setIsMobileOpen(!isMobileOpen)}
      >
        {isMobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </Button>

      <ThemeToggle className="fixed top-4 right-4 z-50 lg:hidden text-foreground" />

      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      <aside className={cn(
        'fixed left-0 top-0 z-40 h-screen w-64 bg-sidebar border-r border-sidebar-border transition-transform lg:translate-x-0',
        isMobileOpen ? 'translate-x-0' : '-translate-x-full'
      )}>
        <div className="flex h-full flex-col">
          <div className="flex h-16 items-center gap-3 px-6 border-b border-sidebar-border">
            <PromptLabIcon size={40} className="w-10 h-10 object-contain" />
            <span className="flex-1 text-lg font-semibold text-sidebar-foreground">PromptLab</span>
            <ThemeToggle className="text-sidebar-foreground hover:text-primary" />
          </div>

          <nav className="flex-1 px-3 py-4 space-y-1">
            {navItems.map((item) => {
              const isActive = pathname === item.href ||
                (item.href !== '/dashboard' && pathname.startsWith(item.href))

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setIsMobileOpen(false)}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-sidebar-accent text-primary'
                      : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground'
                  )}
                >
                  <item.icon className={cn(
                    'h-5 w-5',
                    isActive ? 'text-primary' : 'text-sidebar-foreground/50'
                  )} />
                  {item.title}
                </Link>
              )
            })}
          </nav>

          <div className="p-3 border-t border-sidebar-border">
            <button
              type="button"
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors"
            >
              <LogOut className="h-5 w-5 text-sidebar-foreground/50" />
              Sign Out
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
