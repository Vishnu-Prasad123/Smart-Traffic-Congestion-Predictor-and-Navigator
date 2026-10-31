import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Footer from "./components/Footer.jsx";
import Home from "./pages/Home.jsx";
import RoutePlanner from "./pages/RoutePlanner.jsx";
import Analytics from "./pages/Analytics.jsx";
import ModelPerformance from "./pages/ModelPerformance.jsx";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/planner" element={<RoutePlanner />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/model" element={<ModelPerformance />} />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}
