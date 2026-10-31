import axios from "axios";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api";

const api = axios.create({ baseURL: API_BASE, timeout: 30000 });

export const checkHealth = () => api.get("/health").then(r => r.data);

export const predictCongestion = (payload) =>
  api.post("/predict-congestion", payload).then(r => r.data);

export const calculateRoutes = (source, destination, avoidCongestion = true) =>
  api.post("/routes", { source, destination, avoid_congestion: avoidCongestion }).then(r => r.data);

export const getTrafficSummary = () =>
  api.get("/traffic/summary").then(r => r.data);

export const getModelMetrics = () =>
  api.get("/model/metrics").then(r => r.data);

export const getDiagnosticReport = () =>
  api.get("/traffic/diagnostic-report").then(r => r.data);

export default api;

