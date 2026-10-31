import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, CartesianGrid,
} from "recharts";
import { Brain, CheckCircle, AlertCircle, BarChart2, Info } from "lucide-react";
import DemoModeBanner from "../components/DemoModeBanner.jsx";
import { LoadingSpinner } from "../components/Loading.jsx";
import ErrorMessage from "../components/ErrorMessage.jsx";
import { getModelMetrics } from "../services/api.js";

function MetricCard({ label, value, sub, color = "blue", trained }) {
  if (!trained || value === undefined || value === null) return (
    <div className="card opacity-50">
      <p className="text-slate-400 text-xs mb-1">{label}</p>
      <p className="text-slate-400 text-sm">Not trained</p>
    </div>
  );
  return (
    <div className={`card border-l-4 border-${color}-400`}>
      <p className="text-slate-500 text-xs mb-1">{label}</p>
      <p className="text-2xl font-bold text-slate-800">{(value * 100).toFixed(1)}%</p>
      {sub && <p className="text-xs text-slate-400">{sub}</p>}
    </div>
  );
}

function ConfusionMatrix({ matrix, classes }) {
  if (!matrix || !classes) return null;
  const maxVal = Math.max(...matrix.flat());
  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-sm mx-auto">
        <thead>
          <tr>
            <th className="p-2 text-slate-400 text-xs">Pred?</th>
            {classes.map(c => <th key={c} className="p-2 font-semibold text-slate-700 min-w-[70px]">{c}</th>)}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={i}>
              <td className="p-2 font-semibold text-slate-700 text-xs">{classes[i]}</td>
              {row.map((val, j) => {
                const intensity = maxVal > 0 ? val / maxVal : 0;
                const isDiag = i === j;
                return (
                  <td key={j}
                    className="p-2 text-center rounded font-semibold"
                    style={{
                      background: isDiag
                        ? `rgba(37, 99, 235, ${0.15 + intensity * 0.7})`
                        : `rgba(220, 38, 38, ${intensity * 0.5})`,
                      color: intensity > 0.5 ? "white" : isDiag ? "#1d4ed8" : "#dc2626",
                    }}
                  >
                    {val}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-slate-400 text-center mt-2">Rows = Actual · Columns = Predicted</p>
    </div>
  );
}

export default function ModelPerformance() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const d = await getModelMetrics();
      setData(d);
    } catch (e) {
      setError(e.response?.data?.detail || e.message || "Failed to load metrics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  if (loading) return <div className="p-8"><LoadingSpinner message="Loading model metrics..." /></div>;
  if (error) return <div className="p-8"><ErrorMessage message={error} onRetry={load} /></div>;
  if (!data) return null;

  const trained = data.model_trained;

  // Feature importance chart data
  const fiData = data.feature_importance
    ? Object.entries(data.feature_importance)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10)
        .map(([name, val]) => ({ name: name.replace(" (%)", "").replace(" (km/h)", ""), value: +(val * 100).toFixed(2) }))
    : [];

  // Per-class metrics
  const classData = data.classes?.map(cls => ({
    class: cls,
    precision: data.precision_per_class?.[cls] || 0,
    recall: data.recall_per_class?.[cls] || 0,
    f1: data.f1_per_class?.[cls] || 0,
  })) || [];

  const CLASS_COLORS = { LOW: "#16a34a", MEDIUM: "#d97706", HIGH: "#dc2626" };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-blue-900 flex items-center gap-2">
            <Brain size={28} /> Model Performance
          </h1>
          <p className="text-slate-500 mt-1">
            RandomForestClassifier — trained on Bangalore Traffic Pulse
          </p>
        </div>
        <div className="flex items-center gap-2">
          {trained
            ? <span className="flex items-center gap-1.5 bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium"><CheckCircle size={14} /> Model Trained</span>
            : <span className="flex items-center gap-1.5 bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-medium"><AlertCircle size={14} /> Not Trained</span>
          }
          {data.is_demo_mode && <span className="badge-demo">Demo Data</span>}
        </div>
      </div>

      {data.is_demo_mode && <DemoModeBanner />}

      {!trained && (
        <div className="card bg-amber-50 border-amber-200">
          <div className="flex items-start gap-3">
            <Info size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-800 mb-1">{data.training_message}</p>
              <pre className="text-xs text-amber-700 bg-amber-100 rounded p-3 mt-2">
{`cd smart-traffic-navigator/ml
python preprocessing.py
python train.py
python evaluate.py`}
              </pre>
            </div>
          </div>
        </div>
      )}

      {/* Overall metrics */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Accuracy" value={data.accuracy} trained={trained} color="blue" />
        <MetricCard label="Macro F1-Score" value={data.macro_f1} trained={trained} color="green" />
        <MetricCard label="F1 — LOW" value={data.f1_per_class?.LOW} trained={trained} color="green" />
        <MetricCard label="F1 — HIGH" value={data.f1_per_class?.HIGH} trained={trained} color="red" />
      </div>

      {/* Dataset info */}
      <div className="card">
        <h2 className="font-semibold text-slate-800 mb-3">Dataset & Split Information</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          {[
            ["Total Records", data.total_records?.toLocaleString() || "—"],
            ["Test Set Size", data.test_set_size?.toLocaleString() || "—"],
            ["Features Used", data.n_features || "—"],
            ["Model", data.model || "RandomForestClassifier"],
          ].map(([k, v]) => (
            <div key={k} className="bg-slate-50 rounded-lg p-3">
              <p className="text-slate-500 text-xs">{k}</p>
              <p className="font-semibold text-slate-800 mt-0.5">{v}</p>
            </div>
          ))}
        </div>
        <div className="mt-3 text-xs text-slate-500">
          Split: 70% train / 15% validation / 15% test (stratified). Trained with{" "}
          <code>RandomForestClassifier(n_estimators=200, class_weight=&apos;balanced&apos;)</code>.
        </div>
      </div>

      {/* Per-class metrics + Confusion matrix */}
      <div className="grid md:grid-cols-2 gap-6">
        {classData.length > 0 && (
          <div className="card">
            <h2 className="font-semibold text-slate-800 mb-4">Per-Class Metrics</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={classData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="class" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} tickFormatter={v => `${(v*100).toFixed(0)}%`} />
                <Tooltip formatter={v => `${(v*100).toFixed(1)}%`} />
                <Bar dataKey="precision" name="Precision" fill="#2563EB" radius={[3,3,0,0]} />
                <Bar dataKey="recall" name="Recall" fill="#16a34a" radius={[3,3,0,0]} />
                <Bar dataKey="f1" name="F1" fill="#d97706" radius={[3,3,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-4">Confusion Matrix</h2>
          {trained && data.confusion_matrix
            ? <ConfusionMatrix matrix={data.confusion_matrix} classes={data.classes} />
            : <div className="text-slate-400 text-sm py-8 text-center">Train the model to see confusion matrix</div>
          }
        </div>
      </div>

      {/* Feature importance */}
      {fiData.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-1">Feature Importance</h2>
          <p className="text-xs text-slate-400 mb-4">Mean Decrease in Impurity (MDI) from Random Forest</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={fiData} layout="vertical" margin={{ left: 100, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} unit="%" />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={100} />
              <Tooltip formatter={(v) => `${v}%`} />
              <Bar dataKey="value" fill="#2563EB" radius={[0,4,4,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Feature names */}
      {data.feature_names && (
        <div className="card">
          <h2 className="font-semibold text-slate-800 mb-2">Features Used for Training</h2>
          <div className="flex flex-wrap gap-2">
            {data.feature_names.map(f => (
              <span key={f} className="bg-blue-50 text-blue-700 text-xs px-2.5 py-1 rounded-full">{f}</span>
            ))}
          </div>
          <p className="text-xs text-amber-700 mt-3">
            ? "Congestion Level" (raw target) is excluded from features to prevent target leakage.
          </p>
        </div>
      )}
    </div>
  );
}
