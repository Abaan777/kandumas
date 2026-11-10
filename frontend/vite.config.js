import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Bind to all interfaces (both 127.0.0.1 and ::1) -- Vite's default "localhost"
    // binding can end up IPv6-only ([::1]) on some Windows setups, which makes the
    // page unreachable from a browser that resolves localhost to the IPv4 address.
    host: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
    css: true,
  },
});
