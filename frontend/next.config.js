/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  serverExternalPackages: [
    'firebase',
    '@firebase/app',
    '@firebase/auth',
    '@firebase/firestore',
    '@firebase/util',
    '@firebase/component',
    '@firebase/logger',
  ],
  turbopack: {
    resolveAlias: {
      'firebase/app': 'firebase/app/dist/esm/index.esm.js',
      'firebase/auth': 'firebase/auth/dist/esm/index.esm.js',
      'firebase/firestore': 'firebase/firestore/dist/esm/index.esm.js',
    },
  },
}

module.exports = nextConfig
