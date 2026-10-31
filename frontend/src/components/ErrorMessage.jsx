import { AlertCircle, RefreshCw } from "lucide-react";

export default function ErrorMessage({ message, onRetry }) {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
      <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={18} />
      <div className="flex-1">
        <p className="text-red-800 text-sm">{message}</p>
        {onRetry && (
          <button onClick={onRetry} className="mt-2 text-red-600 hover:text-red-800 text-xs flex items-center gap-1">
            <RefreshCw size={12} /> Try again
          </button>
        )}
      </div>
    </div>
  );
}
