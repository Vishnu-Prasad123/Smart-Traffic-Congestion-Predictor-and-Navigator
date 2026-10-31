export default function Footer() {
  return (
    <footer className="bg-blue-900 text-blue-300 text-sm mt-auto">
      <div className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div>
          <h3 className="text-white font-semibold mb-2">Smart Traffic Navigator</h3>
          <p className="text-blue-400 text-xs leading-relaxed">
            Bengaluru congestion estimation using Random Forest ML and A* routing on
            OpenStreetMap road data. College-level full-stack project.
          </p>
        </div>
        <div>
          <h3 className="text-white font-semibold mb-2">Data Sources</h3>
          <ul className="text-blue-400 text-xs space-y-1">
            <li>Bangalore Traffic Pulse (Kaggle)</li>
            <li>OpenStreetMap via OSMnx</li>
            <li>Demo mode when real data unavailable</li>
          </ul>
        </div>
        <div>
          <h3 className="text-white font-semibold mb-2">Limitations</h3>
          <ul className="text-blue-400 text-xs space-y-1">
            <li>Area-level estimates, not road-level measurements</li>
            <li>Not a real-time traffic system</li>
            <li>Historical patterns only</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-blue-800 text-center py-3 text-blue-500 text-xs">
        2024 Smart Traffic Navigator  Built with React, FastAPI & Scikit-learn
      </div>
    </footer>
  );
}
