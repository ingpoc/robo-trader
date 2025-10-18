import { ReactNode } from 'react'
import '@/styles/globals.css'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <html lang="en">
      <body className="font-sans">
        <div id="root">{children}</div>
      </body>
    </html>
  )
}