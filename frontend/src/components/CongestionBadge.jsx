export default function CongestionBadge({ level, className = "" }) {
  const styles = {
    LOW: "badge-low",
    MEDIUM: "badge-medium",
    HIGH: "badge-high",
    HARD: "badge-high",
  };
  const labels = {
    LOW: "Low",
    MEDIUM: "Medium",
    HIGH: "Hard",
    HARD: "Hard",
  };
  if (!level) return null;
  return (
    <span className={`${styles[level] || "badge-demo"} ${className}`}>
      {labels[level] || level}
    </span>
  );
}
