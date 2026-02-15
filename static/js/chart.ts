import Chart from 'chart.js/auto';

interface DistributionChartConfig {
  labels: string[];
  values: number[];
  x_values: number[];
}

export class DistributionChart {
  private chart: Chart | null = null;
  private canvas: HTMLCanvasElement;

  constructor(canvasId: string) {
    const canvas = document.getElementById(canvasId) as HTMLCanvasElement;
    if (!canvas) {
      throw new Error(`Canvas with id "${canvasId}" not found`);
    }
    this.canvas = canvas;
  }

  render(data: DistributionChartConfig): void {
    if (this.chart) {
      this.chart.destroy();
    }

    const ctx = this.canvas.getContext('2d');
    if (!ctx) return;

    const gradient = ctx.createLinearGradient(0, 0, 0, 320);
    gradient.addColorStop(0, 'rgba(20, 184, 166, 0.8)');
    gradient.addColorStop(1, 'rgba(20, 184, 166, 0.1)');

    this.chart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Probabilidad (%)',
          data: data.values,
          backgroundColor: gradient,
          borderColor: 'rgba(20, 184, 166, 1)',
          borderWidth: 1,
          borderRadius: 4,
          borderSkipped: false,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.9)',
            titleColor: '#e2e8f0',
            bodyColor: '#94a3b8',
            borderColor: 'rgba(20, 184, 166, 0.3)',
            borderWidth: 1,
            padding: 12,
            cornerRadius: 8,
            displayColors: false,
            callbacks: {
              label: (context) => `Probabilidad: ${context.raw.toFixed(4)}%`
            }
          }
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(148, 163, 184, 0.1)',
              drawBorder: false
            },
            ticks: {
              color: '#64748b',
              font: {
                family: 'DM Sans',
                size: 10
              },
              maxRotation: 45,
              minRotation: 45
            }
          },
          y: {
            beginAtZero: true,
            grid: {
              color: 'rgba(148, 163, 184, 0.1)',
              drawBorder: false
            },
            ticks: {
              color: '#64748b',
              font: {
                family: 'DM Sans'
              },
              callback: (value) => `${value}%`
            }
          }
        },
        animation: {
          duration: 1000,
          easing: 'easeOutQuart'
        }
      }
    });
  }

  destroy(): void {
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }
  }

  update(data: DistributionChartConfig): void {
    if (this.chart) {
      this.chart.data.labels = data.labels;
      this.chart.data.datasets[0].data = data.values;
      this.chart.update();
    } else {
      this.render(data);
    }
  }
}

export function initializeChart(chartData: DistributionChartConfig): DistributionChart | null {
  const canvas = document.getElementById('distributionChart');
  if (!canvas || !chartData) return null;
  
  const chart = new DistributionChart('distributionChart');
  chart.render(chartData);
  return chart;
}

declare global {
  interface Window {
    initializeChart: (data: DistributionChartConfig) => DistributionChart | null;
  }
}

if (typeof window !== 'undefined') {
  window.initializeChart = initializeChart;
}
