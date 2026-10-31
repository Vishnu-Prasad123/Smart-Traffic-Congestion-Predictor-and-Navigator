import { NavLink } from "react-router-dom";
import { MapPin, BarChart2, Brain, Navigation } from "lucide-react";

const links = [
  { to: "/", label: "Home", icon: MapPin },
  { to: "/planner", label: "Route Planner", icon: Navigation },
  { to: "/analytics", label: "Analytics", icon: BarChart2 },
  { to: "/model", label: "Model Performance", icon: Brain },
];

export default function Navbar() {
  return (
    <header className="bg-blue-900 text-white shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <NavLink to="/" className="flex items-center gap-2 font-bold text-xl tracking-tight">
          <span className="text-blue-300"></span>
          <span>Smart Traffic Navigator</span>
          <span className="text-blue-400 text-xs font-normal hidden sm:block">Bengaluru</span>
        </NavLink>
        <nav className="hidden md:flex items-center gap-1">
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive ? "bg-blue-700 text-white" : "text-blue-200 hover:bg-blue-800 hover:text-white"
                }`
              }
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </nav>
        <nav className="flex md:hidden items-center gap-1">
          {links.map(({ to, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `p-2 rounded-lg ${isActive ? "bg-blue-700" : "text-blue-300 hover:bg-blue-800"}`
              }
            >
              <Icon size={20} />
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
