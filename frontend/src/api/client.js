import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

const client = axios.create({ baseURL });

client.interceptors.request.use((config) => {
  const token = localStorage.getItem("kandumas_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem("kandumas_token");
      localStorage.removeItem("kandumas_user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default client;

export const login = (username, password) => client.post("/auth/login", { username, password });
export const register = (username, password) => client.post("/auth/register", { username, password });
export const forgotPassword = (username) => client.post("/auth/forgot-password", { username });
export const resetPassword = (token, newPassword) =>
  client.post("/auth/reset-password", { token, new_password: newPassword });
export const getRegions = () => client.get("/meta/regions");
export const getSpecies = () => client.get("/meta/species");
export const getDashboardOverview = () => client.get("/dashboard/overview");
export const getHistorical = (params) => client.get("/historical", { params });
export const postPredict = (payload) => client.post("/predict", payload);
export const getRegionAccuracy = (species) => client.get("/predict/accuracy", { params: { species } });
export const getDailyEstimate = (region, species, date) =>
  client.get("/predict/daily", { params: { region, species, date } });
export const getAdminMetrics = () => client.get("/admin/metrics");
export const refreshDatasets = () => client.post("/admin/datasets/refresh");
export const retrainModels = () => client.post("/admin/retrain");

// Auth is required on this endpoint, so it can't be a plain <a href> link -- fetch it
// with the Authorization header attached and hand the browser a blob to save instead.
export const downloadReport = (params) => client.get("/reports/download", { params, responseType: "blob" });
