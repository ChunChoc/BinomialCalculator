from typing import Dict, Any, Optional, Tuple, Literal
from dataclasses import dataclass
from enum import Enum


class DistributionType(Enum):
    BINOMIAL = "binomial"
    HYPERGEOMETRIC = "hypergeometric"


@dataclass
class ModelDecision:
    distribution_type: DistributionType
    reason: str
    sample_ratio: float
    threshold_used: float
    recommendation: Optional[str] = None


class ModelSelector:
    THRESHOLD = 0.20
    
    @staticmethod
    def decide(N: int, K: int, n: int) -> ModelDecision:
        if N <= 0:
            raise ValueError("La población (N) debe ser mayor que 0")
        if K < 0:
            raise ValueError("Los éxitos en población (K) no pueden ser negativos")
        if K > N:
            raise ValueError("K no puede ser mayor que N")
        if n <= 0:
            raise ValueError("El tamaño de muestra (n) debe ser mayor que 0")
        if n > N:
            raise ValueError("La muestra (n) no puede ser mayor que la población (N)")
        
        sample_ratio = n / N
        threshold = ModelSelector.THRESHOLD
        
        if sample_ratio >= threshold:
            distribution_type = DistributionType.HYPERGEOMETRIC
            reason = (
                f"La muestra representa el {sample_ratio*100:.2f}% de la población "
                f"(≥{threshold*100:.0f}%). Se usa Distribución Hipergeométrica porque "
                f"el muestreo sin reemplazo afecta significativamente las probabilidades."
            )
            recommendation = None
        else:
            distribution_type = DistributionType.BINOMIAL
            reason = (
                f"La muestra representa el {sample_ratio*100:.2f}% de la población "
                f"(<{threshold*100:.0f}%). Se usa Distribución Binomial como aproximación "
                f"porque el efecto del muestreo sin reemplazo es despreciable."
            )
            recommendation = (
                f"Para mayor precisión, considere usar la Distribución Hipergeométrica. "
                f"La Binomial es una buena aproximación cuando n/N < {threshold*100:.0f}%."
            )
        
        return ModelDecision(
            distribution_type=distribution_type,
            reason=reason,
            sample_ratio=round(sample_ratio, 4),
            threshold_used=threshold,
            recommendation=recommendation,
        )
    
    @staticmethod
    def get_distribution_params(N: int, K: int, n: int, x: Optional[int] = None) -> Dict[str, Any]:
        decision = ModelSelector.decide(N, K, n)
        p = K / N
        
        params = {
            'decision': decision,
            'N': N,
            'K': K,
            'n': n,
            'x': x,
            'p': round(p, 6),
        }
        
        if decision.distribution_type == DistributionType.BINOMIAL:
            params['distribution_params'] = {
                'n': n,
                'p': round(p, 6),
                'x': x,
                'N': N,
            }
        else:
            params['distribution_params'] = {
                'N': N,
                'K': K,
                'n': n,
                'x': x,
            }
        
        return params
    
    @staticmethod
    def calculate_with_auto_selection(N: int, K: int, n: int, x: Optional[int] = None) -> Dict[str, Any]:
        from services.distributions import DistributionFactory, BinomialDistribution, HypergeometricDistribution
        
        params = ModelSelector.get_distribution_params(N, K, n, x)
        decision = params['decision']
        
        distribution_type = decision.distribution_type.value
        distribution = DistributionFactory.create(distribution_type)
        
        dist_params = params['distribution_params']
        results = distribution.calculate(**dist_params)
        
        x_values, probabilities = distribution.get_probabilities(**{k: v for k, v in dist_params.items() if k != 'x'})
        
        cumulative_probs = []
        cumulative_sum = 0
        for prob in probabilities:
            cumulative_sum += prob
            cumulative_probs.append(round(cumulative_sum, 4))
        
        return {
            'model_decision': {
                'distribution_type': decision.distribution_type.value,
                'distribution_name': 'Hipergeométrica' if decision.distribution_type == DistributionType.HYPERGEOMETRIC else 'Binomial',
                'reason': decision.reason,
                'sample_ratio': decision.sample_ratio,
                'threshold': decision.threshold_used,
                'recommendation': decision.recommendation,
            },
            'results': results,
            'chart_data': {
                'x_values': x_values,
                'probabilities': probabilities,
                'cumulative': cumulative_probs,
            },
            'input_params': {
                'N': N,
                'K': K,
                'n': n,
                'x': x,
                'p': round(K / N, 6),
            },
        }
