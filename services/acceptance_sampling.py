from __future__ import annotations

import math
from typing import Any, Dict, List

from scipy import stats


class AcceptanceSamplingService:
    POPULATION_THRESHOLD = 0.05

    @staticmethod
    def _validate_inputs(N: int, n: int, c: int, p: float, limite_tolerancia: float) -> None:
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

    @staticmethod
    def _finite_population_correction(n: int, N: int) -> float:
        if n >= N:
            return 0.0
        if N <= 1:
            return 1.0
        return math.sqrt((N - n) / (N - 1))

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
    def calculate(cls, N: int, n: int, c: int, p: float, limite_tolerancia: float) -> Dict[str, Any]:
        cls._validate_inputs(N, n, c, p, limite_tolerancia)

        tolerance_decimal = limite_tolerancia / 100

        x_values = list(range(n + 1))
        probabilities = [float(stats.binom.pmf(x, n, p)) for x in x_values]

        cumulative_probs: List[float] = []
        cumulative_sum = 0.0
        for probability in probabilities:
            cumulative_sum += probability
            cumulative_probs.append(cumulative_sum)

        sample_ratio = n / N
        is_finite_population = sample_ratio > cls.POPULATION_THRESHOLD

        mean = n * p
        base_std = math.sqrt(n * p * (1 - p))
        correction_factor = cls._finite_population_correction(n, N) if is_finite_population else 1.0
        std = base_std * correction_factor

        # El limite de tolerancia se ingresa en porcentaje y se compara como decimal.
        closest_index = cls._find_closest_tolerance_index(cumulative_probs, tolerance_decimal)
        closest_x = x_values[closest_index]
        closest_cumulative = cumulative_probs[closest_index]

        rows = []
        for x, probability, cumulative in zip(x_values, probabilities, cumulative_probs):
            rows.append(
                {
                    'x': x,
                    'probability': round(probability * 100, 6),
                    'cumulative_probability': round(cumulative * 100, 6),
                }
            )

        return {
            'inputs': {
                'N': N,
                'n': n,
                'c': c,
                'p': round(p, 6),
                'limite_tolerancia': round(limite_tolerancia, 4),
            },
            'population_type': 'Finita' if is_finite_population else 'Infinita',
            'sample_ratio': round(sample_ratio, 6),
            'statistics': {
                'mean': round(mean, 6),
                'std': round(std, 6),
                'base_std': round(base_std, 6),
                'correction_factor': round(correction_factor, 6) if is_finite_population else None,
            },
            'acceptance_probability': round(cumulative_probs[c] * 100, 6),
            'acceptance_confidence': round(cumulative_probs[c] * 100, 6),
            'rejection_probability': round((1 - cumulative_probs[c]) * 100, 6),
            'accepted_range': {
                'from_x': 0,
                'to_x': c,
            },
            'rows': rows,
            'closest_tolerance': {
                'index': closest_index,
                'x': closest_x,
                'cumulative_probability': round(closest_cumulative * 100, 6),
                'difference': round(abs(closest_cumulative - tolerance_decimal) * 100, 6),
            },
            'conclusion_message': (
                f'El valor acumulado más cercano al límite de tolerancia del {limite_tolerancia:.2f}% '
                f'se encuentra en c = {closest_x} con un valor de {closest_cumulative * 100:.6f}%'
            ),
            'chart_data': {
                'labels': [str(x) for x in x_values],
                'x_values': x_values,
                'probabilities': [round(prob * 100, 6) for prob in probabilities],
                'cumulative': [round(prob * 100, 6) for prob in cumulative_probs],
                'closest_index': closest_index,
                'acceptance_index': c,
                'tolerance': round(limite_tolerancia, 6),
            },
        }
