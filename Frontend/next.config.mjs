/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  experimental: {
    // Disable worker threads — prevents stack-overflow crashes on Windows
    // when webpack compiles large pages (exit code 0xC0000FD).
    workerThreads: false,
    cpus: 1,
  },
}

export default nextConfig
