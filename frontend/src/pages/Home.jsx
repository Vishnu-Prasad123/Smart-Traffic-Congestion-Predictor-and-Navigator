import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { MapPin, Navigation, BarChart2, Brain, Cpu, Route, AlertTriangle } from "lucide-react";
import MapView from "../components/MapView.jsx";

const FEATURE_CARDS = [
  {
    icon: Brain,
    color: "blue",
    title: "Random Forest Prediction",
    desc: "Ensemble of 200 decision trees trained on Bangalore Traffic Pulse data classifies congestion into LOW, MEDIUM, or HIGH.",
  },
  {
    icon: Route,
    color: "green",
    title: "A* Optimal Routing",
    desc: "A* search on the OSMnx Bengaluru road graph finds the fastest path with congestion-adjusted travel time costs.",
  },
  {
    icon: BarChart2,
    color: "purple",
    title: "Traffic Analytics",
    desc: "Visualise congestion patterns by area and day, average speed by congestion level, and top congestion hotspots.",
  },
  {
    icon: Cpu,
    color: "amber",
    title: "Real Road Network",
    desc: "Road intersections and edges sourced from OpenStreetMap via OSMnx, covering Koramangala and surrounding areas.",
  },
];

export default function Home() {
  const navigate = useNavigate();
  const [src, setSrc] = useState("");
  const [dst, setDst] = useState("");

  const BENGALURU_LANDMARKS = {
    "Koramangala": { lat: 12.9352, lng: 77.6245 },
    "Indiranagar": { lat: 12.9784, lng: 77.6408 },
    "MG Road": { lat: 12.9756, lng: 77.6099 },
    "Electronic City": { lat: 12.8451, lng: 77.6602 },
    "Silk Board": { lat: 12.9174, lng: 77.6228 },
  };

  const handleNavigate = () => {
    const srcCoord = BENGALURU_LANDMARKS[src];
    const dstCoord = BENGALURU_LANDMARKS[dst];
    if (srcCoord && dstCoord) {
      navigate("/planner", { state: { source: srcCoord, destination: dstCoord } });
    } else {
      navigate("/planner");
    }
  };

  return (
    <div>
      {/* Hero */}
      <section className="bg-gradient-to-br from-blue-900 via-blue-800 to-blue-700 text-white">
        <div className="max-w-7xl mx-auto px-6 py-16 grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 bg-blue-700/60 text-blue-200 text-xs font-semibold px-3 py-1 rounded-full mb-4">
              <Cpu size={12} /> Random Forest + A* � Bengaluru, India
            </div>
            <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-4">
              Smart Traffic Congestion Predictor & Navigator
            </h1>
            <p className="text-blue-200 text-lg mb-8 leading-relaxed">
              Machine learning meets road-network routing. Estimate congestion levels with
              Random Forest and find optimal routes through Bengaluru with A* search.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 mb-4">
              <select
                className="bg-white/10 border border-white/20 text-black rounded-lg px-4 py-2.5 flex-1 backdrop-blur"
                value={src}
                onChange={e => setSrc(e.target.value)}
              >
                <option value="">Select Source</option>
                {Object.keys(BENGALURU_LANDMARKS).map(k => <option key={k} value={k}>{k}</option>)}
              </select>
              <select
                className="bg-white/10 border border-white/20 text-black rounded-lg px-4 py-2.5 flex-1 backdrop-blur"
                value={dst}
                onChange={e => setDst(e.target.value)}
              >
                <option value="">Select Destination</option>
                {Object.keys(BENGALURU_LANDMARKS).map(k => <option key={k} value={k}>{k}</option>)}
              </select>
              <button onClick={handleNavigate} className="btn-primary flex items-center gap-2 whitespace-nowrap">
                <Navigation size={16} /> Start Navigation
              </button>
            </div>
            <p className="text-blue-300 text-xs">Or click anywhere on the map in Route Planner to set locations</p>
          </div>
          <div className="hidden md:block">
            <MapView
              center={[12.9716, 77.5946]}
              zoom={12}
              className="h-80 rounded-2xl shadow-2xl"
            />
          </div>
        </div>
      </section>

      {/* Algorithm explanation */}
      <section className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-12 grid md:grid-cols-2 gap-10">
          <div>
            <h2 className="text-2xl font-bold text-blue-900 mb-3">Random Forest Classifier</h2>
            <p className="text-slate-600 leading-relaxed mb-4">
              An ensemble of 200 decision trees trained on the{" "}
              <a href="https://www.kaggle.com/datasets/preethamgoud/bangalores-traffic-pulse"
                className="text-blue-600 hover:underline" target="_blank" rel="noreferrer">
                Bangalore Traffic Pulse dataset
              </a>. Each tree votes on congestion level; the majority wins. Features include
              traffic volume, average speed, road capacity utilization, travel time index,
              weather conditions, roadwork activity, and temporal features.
            </p>
            <div className="bg-blue-50 rounded-lg p-4 text-sm text-blue-800 space-y-1">
              <div>Handles non-linear feature interactions</div>
              <div>Resistant to overfitting via bagging</div>
              <div>Produces probability estimates per class</div>
              <div>Feature importance for interpretability</div>
            </div>
          </div>
          <div>
            <h2 className="text-2xl font-bold text-blue-900 mb-3">A* Search Algorithm</h2>
            <p className="text-slate-600 leading-relaxed mb-4">
              A* finds the shortest path through the Bengaluru road graph (nodes = intersections,
              edges = roads). The cost function combines travel time with a congestion penalty;
              the admissible heuristic is Haversine distance  max_speed, ensuring optimality.
            </p>
            <div className="bg-green-50 rounded-lg p-4 text-sm text-green-800 space-y-1">
              <div>Optimal route guaranteed (admissible heuristic)</div>
              <div>Congestion penalty: LOW=0x, MEDIUM=0.3x, HIGH=0.7x</div>
              <div>Up to 3 alternative routes returned</div>
              <div>Graph from OpenStreetMap via OSMnx</div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature cards */}
      <section className="bg-slate-50 py-14">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-bold text-center text-blue-900 mb-10">Features</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {FEATURE_CARDS.map(({ icon: Icon, color, title, desc }) => (
              <div key={title} className="card hover:shadow-md transition-shadow">
                <div className={`w-10 h-10 rounded-lg bg-${color}-100 flex items-center justify-center mb-4`}>
                  <Icon size={22} className={`text-${color}-600`} />
                </div>
                <h3 className="font-semibold text-slate-800 mb-2">{title}</h3>
                <p className="text-slate-500 text-sm leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

    </div>
  );
}
