import { useEffect } from 'react'

type Theme = 'light'

export function useTheme() {
  useEffect(() => {
    const root = window.document.documentElement

    // Dark mode is not visually complete across the product yet.
    // Force the supported theme so pages do not drift into half-styled states.
    root.classList.remove('dark')
    root.classList.add('light')
    localStorage.setItem('theme', 'light')
  }, [])

  return { theme: 'light' as Theme }
}
