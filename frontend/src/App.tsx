import { BrowserRouter, Routes, Route } from "react-router-dom";
import { RepositoryList } from "./components/RepositoryList";
import { RepositoryView } from "./pages/RepositoryView";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RepositoryList />} />
        <Route path="/repo/:id" element={<RepositoryView />} />
      </Routes>
    </BrowserRouter>
  );
}
