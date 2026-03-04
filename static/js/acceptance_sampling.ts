import Chart from 'chart.js/auto';

declare const document: any;
declare const window: any;
type HTMLCanvasElement = any;

interface AcceptanceRow {
  x: number;
  probability: number;
  cumulative_probability: number;
}

interface AcceptanceChartData {
  labels: string[];
  x_values: number[];
  probabilities: number[];
  cumulative: number[];
  closest_index: number;
  acceptance_index: number;
  tolerance: number;
}

interface AcceptancePayload {
  chartData: AcceptanceChartData;
  rows: AcceptanceRow[];
  tableBodyId?: string;
  probabilityCanvasId?: string;
  cumulativeCanvasId?: string;
}

export function renderAcceptanceSampling(payload: AcceptancePayload): void {
  const {
    chartData,
    rows,
    tableBodyId = 'acceptanceTableBody',
    probabilityCanvasId = 'acceptanceProbabilityChart',
    cumulativeCanvasId = 'acceptanceCumulativeChart',
  } = payload;

  const tableBody = document.getElementById(tableBodyId);
  if (tableBody) {
    tableBody.innerHTML = '';
    rows.forEach((row, index) => {
      const tr = document.createElement('tr');
      const isClosest = index === chartData.closest_index;
      tr.className = isClosest
        ? 'border-b border-emerald-400/30 bg-emerald-500/15'
        : 'border-b border-slate-700/50 hover:bg-slate-700/30';

      tr.innerHTML = `
        <td class="py-2 px-3 text-white font-medium">${row.x}</td>
        <td class="py-2 px-3 text-right text-slate-300">${row.probability.toFixed(6)}%</td>
        <td class="py-2 px-3 text-right ${
          isClosest ? 'text-emerald-300 font-semibold' : 'text-teal-300'
        }">${row.cumulative_probability.toFixed(6)}%</td>
      `;

      tableBody.appendChild(tr);
    });
  }

  const probabilityCanvas = document.getElementById(probabilityCanvasId) as HTMLCanvasElement | null;
  if (probabilityCanvas) {
    new Chart(probabilityCanvas, {
      type: 'bar',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: 'P(x)',
            data: chartData.probabilities,
            backgroundColor: chartData.x_values.map((x, index) => {
              if (index === chartData.closest_index) {
                return 'rgba(16, 185, 129, 0.9)';
              }
              return x <= chartData.acceptance_index
                ? 'rgba(20, 184, 166, 0.85)'
                : 'rgba(100, 116, 139, 0.45)';
            }),
            borderColor: chartData.x_values.map((x, index) => {
              if (index === chartData.closest_index) {
                return 'rgba(16, 185, 129, 1)';
              }
              return x <= chartData.acceptance_index
                ? 'rgba(20, 184, 166, 1)'
                : 'rgba(100, 116, 139, 0.7)';
            }),
            borderWidth: 1,
            borderRadius: 4,
            borderSkipped: false,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: '#94a3b8',
            },
          },
        },
        scales: {
          x: {
            ticks: { color: '#64748b' },
            grid: { color: 'rgba(148,163,184,0.1)' },
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: '#64748b',
              callback: (value) => `${value}%`,
            },
            grid: { color: 'rgba(148,163,184,0.1)' },
          },
        },
      },
    });
  }

  const cumulativeCanvas = document.getElementById(cumulativeCanvasId) as HTMLCanvasElement | null;
  if (cumulativeCanvas) {
    new Chart(cumulativeCanvas, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: [
          {
            label: 'P Acumulada',
            data: chartData.cumulative,
            borderColor: 'rgba(45, 212, 191, 1)',
            backgroundColor: 'rgba(45, 212, 191, 0.15)',
            borderWidth: 2,
            fill: true,
            tension: 0.2,
            pointRadius: chartData.x_values.map((_, index) =>
              index === chartData.closest_index ? 5 : 2
            ),
            pointBackgroundColor: chartData.x_values.map((_, index) =>
              index === chartData.closest_index ? 'rgba(16, 185, 129, 1)' : 'rgba(45, 212, 191, 0.9)'
            ),
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: '#94a3b8',
            },
          },
        },
        scales: {
          x: {
            ticks: { color: '#64748b' },
            grid: { color: 'rgba(148,163,184,0.1)' },
          },
          y: {
            beginAtZero: true,
            max: 100,
            ticks: {
              color: '#64748b',
              callback: (value) => `${value}%`,
            },
            grid: { color: 'rgba(148,163,184,0.1)' },
          },
        },
      },
    });
  }
}

declare global {
  interface Window {
    renderAcceptanceSampling: (payload: AcceptancePayload) => void;
  }
}

if (typeof window !== 'undefined') {
  window.renderAcceptanceSampling = renderAcceptanceSampling;
}
