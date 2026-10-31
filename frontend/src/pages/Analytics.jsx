import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend,
  PieChart, Pie, Cell, LineChart, Line, CartesianGrid,
} from "recharts";
import { BarChart2, TrendingUp, MapPin, Database } from "lucide-react";
import DemoModeBanner from "../components/DemoModeBanner.jsx";
import { LoadingSpinner } from "../components/Loading.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import CongestionBadge from "../components/CongestionBadge.jsx";
import { getTrafficSummary } from "../services/api.js";

const COLORS = { LOW: "#16a34a", MEDIUM: "#d97706", HIGH: "#dc2626" };
const PIE_COLORS = ["#16a34a", "#d97706", "#dc2626"];

function StatCard({ label, value, sub, icon: Icon, color = "blue" }) {
  return (
    <div className="card flex items-start gap-4">
      <div className={`w-10 h-10 rounded-lg bg-${color}-100 flex-shrink-0 flex items-center justify-center`}>
        <Icon size={20} className={`text-${color}-600`} />
      </div>
      <div>
        <p className="text-2xl font-bold text-slate-800">{value}</p>
        <p className="text-sm font-medium text-slate-700">{label}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function Analytics() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const summary = await getTrafficSummary();
      setData(summary);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Failed to load analytics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="p-8"><LoadingSpinner message="Loading traffic analytics..." /></div>;
  if (error) return <div className="p-8"><ErrorMessage message={error} onRetry={load} /></div>;
  if (!data) return null;

  const congDist = [
    { name: "Low", value: data.congestion_distribution?.LOW || 0, fill: "#16a34a" },
    { name: "Medium", value: data.congestion_distribution?.MEDIUM || 0, fill: "#d97706" },
    { name: "High", value: data.congestion_distribution?.HIGH || 0, fill: "#dc2626" },
  ];

  const volByDay = Object.entries(data.avg_volume_by_day || {}).map(([day, val]) => ({
    day, volume: val,
  }));

  const speedByCong = Object.entries(data.avg_speed_by_congestion || {}).map(([level, speed]) => ({
    level, speed,
  }));

  const totalRecords = data.total_records || 0;
  const dominantCong = Object.entries(data.congestion_distribution || {}).sort((a,b) => b[1]-a[1])[0]?.[0] || "N/A";

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-blue-900 flex items-center gap-2">
            <BarChart2 size={28} /> Traffic Analytics
          </h1>
          <p className="text-slate-500 mt-1">Bangalore Traffic Pulse — Historical congestion patterns</p>
        </div>
        {data.is_demo_mode && <span className="badge-demo">Demo Data</span>}
      </div>

      {data.is_demo_mode && <DemoModeBanner />}

      <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-2 text-xs text-blue-700">
        ?? {data.data_note} · Date range: {data.date_range?.min?.slice(0,10) || "N/A"} to {data.date_range?.max?.slice(0,10) || "N/A"}
      </div>

      {/* Stats */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Records" value={totalRecords.toLocaleString()} icon={Database} color="blue" />
        <StatCard label="Dominant Congestion" value={<CongestionBadge level={dominantCong} />} icon={TrendingUp} color="amber" />
        <StatCard label="Locations Tracked" value={data.top_areas?.length || 0} icon={MapPin} color="green" />
        <StatCard
          label="High Congestion Records"
          value={`${(((data.congestion_distribution?.HIGH || 0) / (totalRecords || 1)) * 100).toFixed(1)}%`}
          icon={BarChart2}
          color="red"
        />
      </div>

      {/* Row 1: Congestion pie + Volume by day */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">Congestion Level Distribution</h2>
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={congDist} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {congDist.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
              </Pie>
              <Tooltip formatter={(v) => v.toLocaleString()} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">Average Traffic Volume by Day of Week</h2>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={volByDay} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="day" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="volume" fill="#2563EB" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Row 2: Speed by congestion + Volume over time */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">Average Speed by Congestion Level (km/h)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={speedByCong} layout="vertical" margin={{ left: 16, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 12 }} unit=" km/h" />
              <YAxis dataKey="level" type="category" tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v) => `${v} km/h`} />
              <Bar dataKey="speed" fill="#16a34a" radius={[0,4,4,0]}>
                {speedByCong.map((entry, i) => (
                  <Cell key={i} fill={COLORS[entry.level] || "#64748b"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-1">Traffic Volume Over Time</h2>
          <p className="text-xs text-slate-400 mb-3">Monthly average (daily dataset has no intra-day hourly breakdowns)</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={(data.volume_over_time || []).slice(0, 18)} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="period" tick={{ fontSize: 10 }} interval={2} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line type="monotone" dataKey="avg_volume" stroke="#2563EB" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top areas table */}
      {data.top_areas?.length > 0 && (
        <div className="card overflow-x-auto">
          <h2 className="font-semibold text-slate-800 mb-4">Top Areas by Traffic Volume</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b border-slate-200">
                <th className="pb-2 pr-4">Area</th>
                <th className="pb-2 pr-4">Avg Volume</th>
                <th className="pb-2 pr-4">Avg Speed</th>
                <th className="pb-2">Dominant Congestion</th>
              </tr>
            </thead>
            <tbody>
              {data.top_areas.map((area) => (
                <tr key={area.area} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-2 pr-4 font-medium">{area.area}</td>
                  <td className="py-2 pr-4">{area.avg_volume?.toFixed(0)}</td>
                  <td className="py-2 pr-4">{area.avg_speed?.toFixed(1)} km/h</td>
                  <td className="py-2"><CongestionBadge level={area.dominant_congestion} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
