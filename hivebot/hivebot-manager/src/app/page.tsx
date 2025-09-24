'use client';

import Link from 'next/link';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center max-w-2xl mx-auto px-6">
          <div className="mb-8">
            <div className="text-6xl mb-4">🐝</div>
            <h1 className="text-5xl font-bold text-gray-900 mb-4">Hivebot Manager</h1>
            <p className="text-xl text-gray-600 mb-8">
              Centralized control center for managing Hummingbot strategy clusters
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Link
              href="/dashboard"
              className="bg-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-all duration-300 border-2 border-transparent hover:border-blue-300"
            >
              <div className="text-3xl mb-3">📊</div>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">Management Dashboard</h2>
              <p className="text-gray-600">
                Full control panel with bot monitoring, strategy management, and real-time activity tracking
              </p>
            </Link>
            
            <Link
              href="/demo"
              className="bg-gradient-to-br from-green-500 to-blue-500 text-white rounded-lg shadow-lg p-6 hover:shadow-xl transition-all duration-300 hover:from-green-600 hover:to-blue-600"
            >
              <div className="text-3xl mb-3">👨‍💼</div>
              <h2 className="text-xl font-semibold mb-2">Personal Trading Demo</h2>
              <p className="text-green-100">
                Interactive demo showing your personal trading dashboard with strategy deployment and management
              </p>
            </Link>
          </div>
          
          <div className="mt-12 text-sm text-gray-500">
            <p>Connect to running Hivebot instances • Add/Remove strategies • Monitor performance</p>
          </div>
        </div>
      </div>
    </div>
  );
}
