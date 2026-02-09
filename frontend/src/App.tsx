import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { AuthProvider } from "@/contexts/AuthContext";
import { ErrorBoundary } from "@/components/ErrorBoundary";

// Layouts
import AppLayout from "@/layouts/AppLayout";

// Pages
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import DraftCreate from "@/pages/DraftCreate";
import DraftsList from "@/pages/DraftsList";
import DraftReview from "@/pages/DraftReview";
import Register from "@/pages/Register";
import RegistreDGI from "@/pages/RegistreDGI";
// import Declarations from "@/pages/Declarations";
import Settings from "@/pages/Settings";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="/" element={<AppLayout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<Dashboard />} />
                <Route path="drafts/new" element={<DraftCreate />} />
                <Route path="drafts" element={<DraftsList />} />
                <Route path="drafts/:id/review" element={<DraftReview />} />
                <Route path="register" element={<Register />} />
                <Route path="registre-dgi" element={<RegistreDGI />} />
                {/* <Route path="declarations" element={<Declarations />} /> */}
                <Route path="settings" element={<Settings />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </BrowserRouter>
          <Toaster />
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;