const env = import.meta.env;

const rawApiUrl = (env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || "http://localhost:8000";
const autoWs = rawApiUrl.replace(/^http:/i, "ws:").replace(/^https:/i, "wss:");

export const config = {
  apiUrl: rawApiUrl,
  wsUrl: (env.VITE_WS_URL as string | undefined)?.replace(/\/$/, "") || autoWs,
  useMocks: String(env.VITE_USE_MOCKS ?? "false") === "true",
  demoMode: String(env.VITE_DEMO_MODE ?? "true") === "true",
  apiPrefix: "/api/v1",
};
