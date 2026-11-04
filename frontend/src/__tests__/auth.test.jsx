import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider, useAuth } from '../context/AuthContext.jsx'
import { AuthPage } from '../pages/Auth.jsx'
import { ProtectedRoute, PublicRoute } from '../components/ProtectedRoute.jsx'
import { api } from '../api.jsx'

// Mock the API module
vi.mock('../api.jsx', () => ({
  api: vi.fn(),
  fmt: (n, d = 2) => (n == null ? '—' : Number(n).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })),
  pnlColor: (n) => (n >= 0 ? 'text-up' : 'text-down'),
  Badge: ({ status }) => <span data-testid="badge">{status}</span>,
  ErrorBox: ({ err }) => err ? <div data-testid="error">{err.message}</div> : null,
  watchlistApi: {
    get: vi.fn(() => Promise.resolve([])),
    add: vi.fn(() => Promise.resolve({})),
    remove: vi.fn(() => Promise.resolve({})),
    symbols: vi.fn(() => Promise.resolve([])),
  },
}))

const renderWithRouter = (ui) => {
  return render(
    <BrowserRouter>
      <AuthProvider>
        {ui}
      </AuthProvider>
    </BrowserRouter>
  )
}

describe('AuthPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('renders login form by default', () => {
    renderWithRouter(<AuthPage />)
    expect(screen.getByText('Login')).toBeInTheDocument()
    expect(screen.getByText('Register')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument()
  })

  it('switches to register mode when clicking Sign up', async () => {
    const user = userEvent.setup()
    renderWithRouter(<AuthPage />)
    await user.click(screen.getByRole('button', { name: /sign up/i }))
    expect(screen.getByLabelText('Confirm Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('switches back to login when clicking Log in', async () => {
    const user = userEvent.setup()
    renderWithRouter(<AuthPage />)
    await user.click(screen.getByRole('button', { name: /sign up/i }))
    await user.click(screen.getByRole('button', { name: /log in/i }))
    expect(screen.getByRole('button', { name: /log in/i })).toBeInTheDocument()
    expect(screen.queryByLabelText('Confirm Password')).not.toBeInTheDocument()
  })

  it('shows validation error for short password', async () => {
    const user = userEvent.setup()
    renderWithRouter(<AuthPage />)
    await user.type(screen.getByLabelText('Email'), 'test@test.com')
    await user.type(screen.getByLabelText('Password'), 'short')
    await user.click(screen.getByRole('button', { name: /log in/i }))
    await waitFor(() => expect(screen.getByText('Password must be at least 12 characters')).toBeInTheDocument())
  })

  it('shows validation error for mismatched passwords on register', async () => {
    const user = userEvent.setup()
    renderWithRouter(<AuthPage />)
    await user.click(screen.getByRole('button', { name: /sign up/i }))
    await user.type(screen.getByLabelText('Email'), 'test@test.com')
    await user.type(screen.getByLabelText('Password'), 'password123456')
    await user.type(screen.getByLabelText('Confirm Password'), 'different')
    await user.click(screen.getByRole('button', { name: /create account/i }))
    await waitFor(() => expect(screen.getByText('Passwords do not match')).toBeInTheDocument())
  })

  it('calls login API on valid login submit', async () => {
    const user = userEvent.setup()
    api.mockResolvedValueOnce({ access_token: 'test-token', token_type: 'bearer' })
    api.mockResolvedValueOnce({ id: 1, email: 'test@test.com', is_active: true, created_at: new Date().toISOString() })

    renderWithRouter(<AuthPage />)
    await user.type(screen.getByLabelText('Email'), 'test@test.com')
    await user.type(screen.getByLabelText('Password'), 'password123456')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    await waitFor(() => {
      expect(api).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email: 'test@test.com', password: 'password123456' }),
      }))
    }, { timeout: 5000 })
  })

  it('calls register API on valid register submit', async () => {
    const user = userEvent.setup()
    api.mockResolvedValueOnce({ id: 1, email: 'new@test.com', is_active: true, created_at: new Date().toISOString() })
    api.mockResolvedValueOnce({ access_token: 'test-token', token_type: 'bearer' })
    api.mockResolvedValueOnce({ id: 1, email: 'new@test.com', is_active: true, created_at: new Date().toISOString() })

    renderWithRouter(<AuthPage />)
    await user.click(screen.getByRole('button', { name: /sign up/i }))
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
    })
    await user.type(screen.getByLabelText('Email'), 'new@test.com')
    await user.type(screen.getByLabelText('Password'), 'password123456')
    await user.type(screen.getByLabelText('Confirm Password'), 'password123456')
    fireEvent.submit(screen.getByTestId('login-form'))

    await waitFor(() => {
      expect(api).toHaveBeenCalledWith('/api/auth/register', expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ email: 'new@test.com', password: 'password123456' }),
      }))
    }, { timeout: 5000 })
  })

  it('shows API error on failed login', async () => {
    const user = userEvent.setup()
    api.mockRejectedValueOnce({ detail: 'Invalid credentials' })

    renderWithRouter(<AuthPage />)
    await user.type(screen.getByLabelText('Email'), 'test@test.com')
    await user.type(screen.getByLabelText('Password'), 'wrongpassword')
    await user.click(screen.getByRole('button', { name: /log in/i }))

    await waitFor(() => expect(screen.getByText('Invalid credentials')).toBeInTheDocument(), { timeout: 5000 })
  })

  it('shows password length requirement on register', async () => {
    const user = userEvent.setup()
    renderWithRouter(<AuthPage />)
    await user.click(screen.getByRole('button', { name: /sign up/i }))
    expect(screen.getByText('Minimum 12 characters, maximum 128 characters')).toBeInTheDocument()
  })
})

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('provides authentication state', () => {
    let contextValue = null
    const TestComponent = () => {
      const auth = useAuth()
      contextValue = auth
      return null
    }

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    )

    expect(contextValue).toEqual({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      login: expect.any(Function),
      register: expect.any(Function),
      logout: expect.any(Function),
      refreshUser: expect.any(Function),
      authenticatedApi: expect.any(Function),
    })
  })

  it('loads user from localStorage on init', async () => {
    const mockUser = { id: 1, email: 'test@test.com', is_active: true, created_at: new Date().toISOString() }
    localStorage.setItem('quantniti_token', 'test-token')
    localStorage.setItem('quantniti_user', JSON.stringify(mockUser))

    let contextValue = null
    const TestComponent = () => {
      const auth = useAuth()
      contextValue = auth
      return null
    }

    render(
      <BrowserRouter>
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(contextValue.isLoading).toBe(false)
      expect(contextValue.isAuthenticated).toBe(true)
      expect(contextValue.user).toEqual(mockUser)
      expect(contextValue.token).toBe('test-token')
    })
  })
})

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('redirects to login when not authenticated', () => {
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <AuthProvider>
          <Routes>
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <div data-testid="protected">Protected Content</div>
                </ProtectedRoute>
              }
            />
            <Route path="/login" element={<div data-testid="login">Login Page</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    )

    // Should redirect to login page
    expect(screen.getByText('Login Page')).toBeInTheDocument()
  })

  it('shows protected content when authenticated', async () => {
    localStorage.setItem('quantniti_token', 'test-token')
    localStorage.setItem('quantniti_user', JSON.stringify({ id: 1, email: 'test@test.com', is_active: true, created_at: new Date().toISOString() }))

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <AuthProvider>
          <Routes>
            <Route
              path="/protected"
              element={
                <ProtectedRoute>
                  <div data-testid="protected">Protected Content</div>
                </ProtectedRoute>
              }
            />
            <Route path="/login" element={<div data-testid="login">Login Page</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Protected Content')).toBeInTheDocument()
    })
  })
})

describe('PublicRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('redirects authenticated users away from login page', async () => {
    localStorage.setItem('quantniti_token', 'test-token')
    localStorage.setItem('quantniti_user', JSON.stringify({ id: 1, email: 'test@test.com', is_active: true, created_at: new Date().toISOString() }))

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <div data-testid="login">Login Page</div>
                </PublicRoute>
              }
            />
            <Route path="/" element={<div data-testid="home">Home</div>} />
            <Route path="/dashboard" element={<div data-testid="dashboard">Dashboard</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Home')).toBeInTheDocument()
    })
  })

  it('shows login page when not authenticated', async () => {
    // Ensure no auth state
    localStorage.clear()

    render(
      <MemoryRouter initialEntries={['/login']}>
        <AuthProvider>
          <Routes>
            <Route
              path="/login"
              element={
                <PublicRoute>
                  <div data-testid="login">Login Page</div>
                </PublicRoute>
              }
            />
            <Route path="/" element={<div data-testid="home">Home</div>} />
            <Route path="/dashboard" element={<div data-testid="dashboard">Dashboard</div>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>
    )

    // Wait for auth initialization to complete (loading -> false)
    await waitFor(() => {
      expect(screen.getByText('Login Page')).toBeInTheDocument()
    }, { timeout: 3000 })
  })
})