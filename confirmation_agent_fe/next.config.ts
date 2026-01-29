import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // basePath: '/SchedulerAgent/CallsStatusLogger',
  trailingSlash: true, // Crucial: coincidir con la '/' del location de Nginx
  // assetPrefix: '/SchedulerAgent/CallStatusLogger', // Prueba comentando esto si el error persiste
};

export default nextConfig;