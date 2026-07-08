import { PLANET_ABBR } from '../i18n'

const S = 300
const A = [0, 0]
const B = [S, 0]
const C = [S, S]
const D = [0, S]
const P = [S / 2, 0]
const Q = [S, S / 2]
const R = [S / 2, S]
const Lm = [0, S / 2]
const O = [S / 2, S / 2]
const Mpq = [(3 * S) / 4, S / 4]
const Mqr = [(3 * S) / 4, (3 * S) / 4]
const Mrl = [S / 4, (3 * S) / 4]
const Mlp = [S / 4, S / 4]

// House polygons in clockwise order, House 1 fixed at the top (N) position.
const HOUSE_POLYGONS = {
  1: [P, Mpq, O, Mlp],
  2: [P, B, Mpq],
  3: [B, Q, Mpq],
  4: [Q, Mqr, O, Mpq],
  5: [Q, C, Mqr],
  6: [C, R, Mqr],
  7: [R, Mrl, O, Mqr],
  8: [R, D, Mrl],
  9: [D, Lm, Mrl],
  10: [Lm, Mlp, O, Mrl],
  11: [Lm, A, Mlp],
  12: [A, P, Mlp],
}

function centroid(points) {
  const n = points.length
  const x = points.reduce((sum, p) => sum + p[0], 0) / n
  const y = points.reduce((sum, p) => sum + p[1], 0) / n
  return [x, y]
}

const HOUSE_CENTROIDS = Object.fromEntries(
  Object.entries(HOUSE_POLYGONS).map(([house, pts]) => [house, centroid(pts)])
)

function polygonPoints(points) {
  return points.map((p) => p.join(',')).join(' ')
}

export default function KundaliChart({ lang, chart }) {
  const lagnaSign = chart.lagna_sign

  const planetsByHouse = {}
  for (const [name, planet] of Object.entries(chart.planets)) {
    if (!planetsByHouse[planet.house]) planetsByHouse[planet.house] = []
    planetsByHouse[planet.house].push(name)
  }

  return (
    <svg viewBox={`0 0 ${S} ${S}`} className="h-auto w-full max-w-md" role="img" aria-label="Kundali chart">
      <rect x="0" y="0" width={S} height={S} fill="#fffdf8" stroke="#6b1a24" strokeWidth="2" />

      <polygon
        points={polygonPoints(HOUSE_POLYGONS[1])}
        fill="#d4af3733"
        stroke="none"
        data-testid="lagna-house"
      />

      <line x1={A[0]} y1={A[1]} x2={C[0]} y2={C[1]} stroke="#6b1a24" strokeWidth="1.5" />
      <line x1={B[0]} y1={B[1]} x2={D[0]} y2={D[1]} stroke="#6b1a24" strokeWidth="1.5" />
      <polygon points={polygonPoints([P, Q, R, Lm])} fill="none" stroke="#6b1a24" strokeWidth="1.5" />

      {Object.entries(HOUSE_CENTROIDS).map(([houseStr, [cx, cy]]) => {
        const house = Number(houseStr)
        const signNumber = ((lagnaSign + house - 1) % 12) + 1
        const planets = planetsByHouse[house] ?? []
        const isLagna = house === 1
        return (
          <g key={house} data-testid={`house-${house}`}>
            <text
              x={cx}
              y={cy - 12}
              fontSize="9"
              textAnchor="middle"
              fill="#96741e"
              fontWeight="600"
            >
              {signNumber}
            </text>
            {isLagna && (
              <text
                x={cx}
                y={cy - 22}
                fontSize="8"
                textAnchor="middle"
                fill="#6b1a24"
                fontWeight="700"
                data-testid="lagna-label"
              >
                Asc
              </text>
            )}
            {planets.map((name, i) => (
              <text
                key={name}
                x={cx}
                y={cy + i * 11}
                fontSize="11"
                textAnchor="middle"
                fill="#3f0f15"
                fontWeight="500"
                data-testid={`planet-${name}`}
              >
                {PLANET_ABBR[name]}
              </text>
            ))}
          </g>
        )
      })}
    </svg>
  )
}
