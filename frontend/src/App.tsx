import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './context/AuthContext'
import { RoleGuard } from './components/RoleGuard'
import { AppShell } from './components/AppShell'
import { LoginPage } from './pages/LoginPage'
import { BookListPage } from './pages/BookListPage'
import { BookDetailPage } from './pages/BookDetailPage'
import { BookFormPage } from './pages/BookFormPage'
import { CategoryEditionManagementPage } from './pages/CategoryEditionManagementPage'
import { UserManagementPage } from './pages/UserManagementPage'
import { AccountPage } from './pages/AccountPage'
import { NotFoundPage } from './pages/NotFoundPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { refetchOnWindowFocus: false },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <RoleGuard>
                  <AppShell>
                    <BookListPage />
                  </AppShell>
                </RoleGuard>
              }
            />
            <Route
              path="/books/new"
              element={
                <RoleGuard minRole="librarian">
                  <AppShell>
                    <BookFormPage />
                  </AppShell>
                </RoleGuard>
              }
            />
            <Route
              path="/books/:id"
              element={
                <RoleGuard>
                  <AppShell>
                    <BookDetailPage />
                  </AppShell>
                </RoleGuard>
              }
            />
            <Route
              path="/books/:id/edit"
              element={
                <RoleGuard minRole="librarian">
                  <AppShell>
                    <BookFormPage />
                  </AppShell>
                </RoleGuard>
              }
            />
            <Route
              path="/categories"
              element={
                <RoleGuard minRole="librarian">
                  <AppShell>
                    <CategoryEditionManagementPage />
                  </AppShell>
                </RoleGuard>
              }
            />
            <Route
              path="/admin/users"
              element={
                <RoleGuard minRole="admin">
                  <AppShell>
                    <UserManagementPage />
                  </AppShell>
                </RoleGuard>
              }
            />
            <Route
              path="/account"
              element={
                <RoleGuard>
                  <AppShell>
                    <AccountPage />
                  </AppShell>
                </RoleGuard>
              }
            />
            <Route path="/404" element={<NotFoundPage />} />
            <Route path="*" element={<Navigate to="/404" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
