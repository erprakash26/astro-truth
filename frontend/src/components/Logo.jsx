// The app's mark: the same rotated-square "diamond" that divides a North
// Indian kundali chart into its four cardinal houses (see the P/Q/R/L
// midpoint polygon in KundaliChart.jsx), with a bindu star at the center
// where every house line of that chart converges.
export default function Logo({ className = 'h-9 w-9' }) {
  return (
    <svg viewBox="0 0 100 100" className={className} role="img" aria-label="AstroTruth logo">
      <path
        d="M50,8 L92,50 L50,92 L8,50 Z"
        fill="none"
        stroke="#d4af37"
        strokeWidth="7"
        strokeLinejoin="round"
      />
      <path
        d="M50,34 L54.24,45.76 L66,50 L54.24,54.24 L50,66 L45.76,54.24 L34,50 L45.76,45.76 Z"
        fill="#fffdf8"
      />
    </svg>
  )
}
