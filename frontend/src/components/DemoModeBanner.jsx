import { AlertTriangle } from "lucide-react";

export default function DemoModeBanner({ message }) {
  return (
    <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 flex items-start gap-3 my-3">
      <AlertTriangle className="text-orange-500 mt-0.5 flex-shrink-0" size={18} />
      <div className="text-sm text-orange-800">
        <span className="font-semibold">Demo Mode — </span>
        {message || "Showing statistically representative demo data. Real Kaggle dataset not found."}
      </div>
    </div>
  );
}
