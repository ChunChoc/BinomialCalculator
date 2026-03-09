from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from scipy import stats
from services.model_selector import DistributionType, ModelSelector


class AcceptanceSamplingService:
    @staticmethod
    def _validate_inputs(N: int, n: int, c: int, p: float, limite_tolerancia: float, K: Optional[int] = None) -> None:
        if N <= 0:
            raise ValueError('El tamaño del lote (N) debe ser mayor que 0')
        if n <= 0:
            raise ValueError('El tamaño de la muestra (n) debe ser mayor que 0')
        if n > N:
            raise ValueError('El tamaño de la muestra (n) no puede ser mayor que el lote (N)')
        if c < 0 or c > n:
            raise ValueError(f'El número de aceptación (c) debe estar entre 0 y {n}')
        if p < 0 or p > 1:
            raise ValueError('La proporción de defectuosos (p) debe estar entre 0 y 1')
        if limite_tolerancia < 0 or limite_tolerancia > 100:
            raise ValueError('El límite de tolerancia debe estar entre 0 y 100')
        if K is not None and (K < 0 or K > N):
            raise ValueError(f'El número de defectuosos (K) debe estar entre 0 y {N}')

    @staticmethod
    def _finite_population_correction(n: int, N: int) -> float:
        if n >= N:
            return 0.0
        if N <= 1:
            return 1.0
        return math.sqrt((N - n) / (N - 1))

    @staticmethod
    def _build_rows(x_values: List[int], probabilities: List[float]) -> Dict[str, Any]:
        cumulative_probs: List[float] = []
        cumulative_sum = 0.0
        rows = []

        for x, probability in zip(x_values, probabilities):
            cumulative_sum += probability
            cumulative_probs.append(cumulative_sum)
            rows.append(
                {
                    'x': x,
                    'probability': round(probability * 100, 6),
                    'cumulative_probability': round(cumulative_sum * 100, 6),
                }
            )

        return {
            'rows': rows,
            'cumulative_probs': cumulative_probs,
        }

    @classmethod
    def _calculate_binomial_distribution(cls, N: int, n: int, c: int, p: float) -> Dict[str, Any]:
        x_values = list(range(n + 1))
        probabilities = [float(stats.binom.pmf(x, n, p)) for x in x_values]
        rows_data = cls._build_rows(x_values, probabilities)

        mean = n * p
        std = math.sqrt(n * p * (1 - p))
        cumulative_probs = rows_data['cumulative_probs']

        return {
            'distribution_key': DistributionType.BINOMIAL.value,
            'distribution_name': 'Binomial',
            'x_values': x_values,
            'probabilities': probabilities,
            'rows': rows_data['rows'],
            'cumulative_probs': cumulative_probs,
            'statistics': {
                'mean': round(mean, 6),
                'std': round(std, 6),
                'base_std': round(std, 6),
                'correction_factor': None,
            },
            'acceptance_probability': round(cumulative_probs[c] * 100, 6),
            'rejection_probability': round((1 - cumulative_probs[c]) * 100, 6),
        }

    @classmethod
    def _calculate_hypergeometric_distribution(cls, N: int, n: int, c: int, p: float, K: Optional[int] = None) -> Dict[str, Any]:
        if K is None:
            K = round(N * p)
        x_values = list(range(n + 1))
        probabilities = [float(stats.hypergeom.pmf(x, N, K, n)) for x in x_values]
        rows_data = cls._build_rows(x_values, probabilities)

        p_effective = K / N
        mean = n * p_effective
        base_std = math.sqrt(n * p_effective * (1 - p_effective))
        correction_factor = cls._finite_population_correction(n, N)
        std = base_std * correction_factor
        cumulative_probs = rows_data['cumulative_probs']

        return {
            'distribution_key': DistributionType.HYPERGEOMETRIC.value,
            'distribution_name': 'Hipergeométrica',
            'K': K,
            'p_effective': round(p_effective, 6),
            'x_values': x_values,
            'probabilities': probabilities,
            'rows': rows_data['rows'],
            'cumulative_probs': cumulative_probs,
            'statistics': {
                'mean': round(mean, 6),
                'std': round(std, 6),
                'base_std': round(base_std, 6),
                'correction_factor': round(correction_factor, 6),
            },
            'acceptance_probability': round(cumulative_probs[c] * 100, 6),
            'rejection_probability': round((1 - cumulative_probs[c]) * 100, 6),
        }

    @staticmethod
    def _find_closest_tolerance_index(cumulative_probs: List[float], tolerance: float) -> int:
        closest_index = 0
        min_difference = float('inf')

        for index, cumulative in enumerate(cumulative_probs):
            # Compara cada acumulado contra la tolerancia para hallar la menor distancia absoluta.
            difference = abs(cumulative - tolerance)
            if difference < min_difference:
                min_difference = difference
                closest_index = index

        return closest_index

    @classmethod
    def calculate(cls, N: int, n: int, c: int, p: float, limite_tolerancia: float, K: Optional[int] = None) -> Dict[str, Any]:
        cls._validate_inputs(N, n, c, p, limite_tolerancia, K)

        tolerance_decimal = limite_tolerancia / 100

        binomial_data = cls._calculate_binomial_distribution(N, n, c, p)
        hypergeometric_data = cls._calculate_hypergeometric_distribution(N, n, c, p, K)

        decision = ModelSelector.decide(N=N, K=hypergeometric_data['K'], n=n)
        selected_distribution_key = decision.distribution_type.value
        selected_data = hypergeometric_data if selected_distribution_key == DistributionType.HYPERGEOMETRIC.value else binomial_data

        sample_ratio = n / N
        cumulative_probs = selected_data['cumulative_probs']
        x_values = selected_data['x_values']

        # El limite de tolerancia se ingresa en porcentaje y se compara como decimal.
        closest_index = cls._find_closest_tolerance_index(cumulative_probs, tolerance_decimal)
        closest_x = x_values[closest_index]
        closest_cumulative = cumulative_probs[closest_index]

        return {
            'inputs': {
                'N': N,
                'n': n,
                'c': c,
                'p': round(p, 6),
                'K': hypergeometric_data['K'],
                'limite_tolerancia': round(limite_tolerancia, 4),
            },
            'population_type': 'Finita',
            'sample_ratio': round(sample_ratio, 6),
            'model_decision': {
                'distribution_type': selected_distribution_key,
                'distribution_name': selected_data['distribution_name'],
                'reason': decision.reason,
                'sample_ratio': decision.sample_ratio,
                'threshold': decision.threshold_used,
                'threshold_percent': round(decision.threshold_used * 100, 2),
            },
            'distribution_comparison': {
                DistributionType.BINOMIAL.value: {
                    'name': binomial_data['distribution_name'],
                    'acceptance_probability': binomial_data['acceptance_probability'],
                    'rejection_probability': binomial_data['rejection_probability'],
                    'mean': binomial_data['statistics']['mean'],
                    'std': binomial_data['statistics']['std'],
                },
                DistributionType.HYPERGEOMETRIC.value: {
                    'name': hypergeometric_data['distribution_name'],
                    'acceptance_probability': hypergeometric_data['acceptance_probability'],
                    'rejection_probability': hypergeometric_data['rejection_probability'],
                    'mean': hypergeometric_data['statistics']['mean'],
                    'std': hypergeometric_data['statistics']['std'],
                    'defectivos_lote': hypergeometric_data['K'],
                    'effective_p': hypergeometric_data['p_effective'],
                },
                'difference': {
                    'acceptance_probability': round(
                        hypergeometric_data['acceptance_probability'] - binomial_data['acceptance_probability'],
                        6,
                    ),
                    'rejection_probability': round(
                        hypergeometric_data['rejection_probability'] - binomial_data['rejection_probability'],
                        6,
                    ),
                },
            },
            'statistics': selected_data['statistics'],
            'acceptance_probability': selected_data['acceptance_probability'],
            'acceptance_confidence': selected_data['acceptance_probability'],
            'rejection_probability': selected_data['rejection_probability'],
            'accepted_range': {
                'from_x': 0,
                'to_x': c,
            },
            'rows': selected_data['rows'],
            'closest_tolerance': {
                'index': closest_index,
                'x': closest_x,
                'cumulative_probability': round(closest_cumulative * 100, 6),
                'difference': round(abs(closest_cumulative - tolerance_decimal) * 100, 6),
            },
            'conclusion_message': (
                f"Se recomienda usar la distribución {selected_data['distribution_name']} porque "
                f'n/N = {sample_ratio * 100:.2f}% y el umbral de validación es {decision.threshold_used * 100:.0f}%. '
                f'El valor acumulado más cercano al límite de tolerancia del {limite_tolerancia:.2f}% '
                f'se encuentra en c = {closest_x} con un valor de {closest_cumulative * 100:.6f}%'
            ),
            'chart_data': {
                'labels': [str(x) for x in x_values],
                'x_values': x_values,
                'probabilities': [round(prob * 100, 6) for prob in selected_data['probabilities']],
                'cumulative': [round(prob * 100, 6) for prob in cumulative_probs],
                'closest_index': closest_index,
                'acceptance_index': c,
                'tolerance': round(limite_tolerancia, 6),
                'distribution_name': selected_data['distribution_name'],
            },
        }
