export default {
    darkMode: ['class'],
    content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
  	extend: {
  		colors: {
  			border: 'hsl(var(--border))',
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			gray: {
  				'50': '#fcfcfc',
  				'100': '#f8f8f8',
  				'200': '#e6e6e6',
  				'300': '#d1d1d1',
  				'400': '#9c9c9c',
  				'500': '#6b6b6b',
  				'600': '#4b4b4b',
  				'700': '#373737',
  				'800': '#1f1f1f',
  				'900': '#111111',
  				'950': '#030303'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				light: '#60a5fa',
  				dark: '#1e40af',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			success: {
  				DEFAULT: '#22c55e',
  				light: '#4ade80',
  				dark: '#16a34a'
  			},
  			warning: {
  				DEFAULT: '#f59e0b',
  				light: '#fef3c7',
  				dark: '#d97706'
  			},
  			error: {
  				DEFAULT: '#ef4444',
  				light: '#fca5a5',
  				dark: '#dc2626'
  			},
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		fontFamily: {
  			sans: [
  				'Inter',
  				'-apple-system',
  				'BlinkMacSystemFont',
  				'Segoe UI',
  				'Roboto',
  				'sans-serif'
  			],
  			mono: [
  				'JetBrains Mono',
  				'Menlo',
  				'Monaco',
  				'Courier New',
  				'monospace'
  			]
  		},
  		fontSize: {
  			'11': [
  				'0.6875rem',
  				{
  					lineHeight: '1rem',
  					letterSpacing: '0.01em'
  				}
  			],
  			'13': [
  				'0.8125rem',
  				{
  					lineHeight: '1.25rem',
  					letterSpacing: '0'
  				}
  			],
  			'32': [
  				'2rem',
  				{
  					lineHeight: '2.5rem',
  					letterSpacing: '-0.02em'
  				}
  			],
  			'2xs': [
  				'0.625rem',
  				{
  					lineHeight: '0.875rem',
  					letterSpacing: '0.02em'
  				}
  			],
  			xs: [
  				'0.75rem',
  				{
  					lineHeight: '1rem',
  					letterSpacing: '0.01em'
  				}
  			],
  			sm: [
  				'0.875rem',
  				{
  					lineHeight: '1.25rem',
  					letterSpacing: '0'
  				}
  			],
  			base: [
  				'1rem',
  				{
  					lineHeight: '1.5rem',
  					letterSpacing: '0'
  				}
  			],
  			lg: [
  				'1.125rem',
  				{
  					lineHeight: '1.75rem',
  					letterSpacing: '-0.01em'
  				}
  			],
  			xl: [
  				'1.25rem',
  				{
  					lineHeight: '1.75rem',
  					letterSpacing: '-0.01em'
  				}
  			],
  			'2xl': [
  				'1.5rem',
  				{
  					lineHeight: '2rem',
  					letterSpacing: '-0.02em'
  				}
  			],
  			'3xl': [
  				'1.875rem',
  				{
  					lineHeight: '2.25rem',
  					letterSpacing: '-0.02em'
  				}
  			],
  			'4xl': [
  				'2.25rem',
  				{
  					lineHeight: '2.5rem',
  					letterSpacing: '-0.03em'
  				}
  			]
  		},
  		spacing: {
  			'1': '8px',
  			'2': '16px',
  			'3': '24px',
  			'4': '32px',
  			'5': '40px',
  			'6': '48px',
  			'7': '56px',
  			'8': '64px',
  			'9': '72px',
  			'10': '80px'
  		},
  		borderRadius: {
  			none: '0',
  			sm: 'calc(var(--radius) - 4px)',
  			DEFAULT: '4px',
  			md: 'calc(var(--radius) - 2px)',
  			lg: 'var(--radius)'
  		},
  		animation: {
  			'fade-in': 'fadeIn 300ms cubic-bezier(0.4, 0, 0.2, 1)',
  			'slide-up': 'slideUp 300ms cubic-bezier(0.4, 0, 0.2, 1)',
  			'slide-in-right': 'slideInRight 300ms cubic-bezier(0.4, 0, 0.2, 1)',
  			'scale-in': 'scaleIn 200ms cubic-bezier(0.4, 0, 0.2, 1)',
  			'bounce-in': 'bounceIn 400ms cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		},
  		keyframes: {
  			fadeIn: {
  				'0%': {
  					opacity: '0'
  				},
  				'100%': {
  					opacity: '1'
  				}
  			},
  			slideUp: {
  				'0%': {
  					opacity: '0',
  					transform: 'translateY(12px)'
  				},
  				'100%': {
  					opacity: '1',
  					transform: 'translateY(0)'
  				}
  			},
  			slideInRight: {
  				'0%': {
  					opacity: '0',
  					transform: 'translateX(-12px)'
  				},
  				'100%': {
  					opacity: '1',
  					transform: 'translateX(0)'
  				}
  			},
  			scaleIn: {
  				'0%': {
  					opacity: '0',
  					transform: 'scale(0.95)'
  				},
  				'100%': {
  					opacity: '1',
  					transform: 'scale(1)'
  				}
  			},
  			bounceIn: {
  				'0%': {
  					opacity: '0',
  					transform: 'scale(0.3)'
  				},
  				'50%': {
  					opacity: '1',
  					transform: 'scale(1.05)'
  				},
  				'70%': {
  					transform: 'scale(0.9)'
  				},
  				'100%': {
  					opacity: '1',
  					transform: 'scale(1)'
  				}
  			},
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		transitionDuration: {
  			DEFAULT: '150ms'
  		},
  		scale: {
  			'1.005': '1.005'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
}
