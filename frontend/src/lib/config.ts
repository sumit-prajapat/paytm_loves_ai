const env = import.meta.env;

export const config = {
  apiUrl: (env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || "http://localhost:8000",
  wsUrl: (env.VITE_WS_URL as string | undefined)?.replace(/\/$/, "") || "ws://localhost:8000",
  useMocks: String(env.VITE_USE_MOCKS ?? "false") === "true",
  demoMode: String(env.VITE_DEMO_MODE ?? "true") === "true",
  apiPrefix: "/api/v1",
};
