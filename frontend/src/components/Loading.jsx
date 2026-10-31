import { Loader2 } from "lucide-react";

export function LoadingSpinner({ message = "Loading..." }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-blue-600">
      <Loader2 size={24} className="animate-spin" />
      <span className="text-slate-600">{message}</span>
    </div>
  );
}

export function LoadingCard() {
  return (
    <div className="card animate-pulse">
      <div className="h-4 bg-slate-200 rounded w-3/4 mb-3"></div>
      <div className="h-4 bg-slate-200 rounded w-1/2"></div>
    </div>
  );
}
