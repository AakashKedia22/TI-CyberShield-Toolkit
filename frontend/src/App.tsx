import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ApiProvider } from "./context";
import { Layout } from "./components/Layout";
import SessionsPage from "./pages/SessionsPage";
import CertificatesPage from "./pages/CertificatesPage";
import ImagesPage from "./pages/ImagesPage";
import ArtifactsPage from "./pages/ArtifactsPage";
import JobsPage from "./pages/JobsPage";
import JobDetailPage from "./pages/JobDetailPage";

export default function App() {
  return (
    <BrowserRouter>
      <ApiProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<SessionsPage />} />
            <Route path="/certificates" element={<CertificatesPage />} />
            <Route path="/images" element={<ImagesPage />} />
            <Route path="/artifacts" element={<ArtifactsPage />} />
            <Route path="/jobs" element={<JobsPage />} />
            <Route path="/jobs/:service/:id" element={<JobDetailPage />} />
          </Routes>
        </Layout>
      </ApiProvider>
    </BrowserRouter>
  );
}