from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, TypedDict, Unpack
import math
from scipy import stats


class BinomialParams(TypedDict, total=False):
    n: int
    p: float
    x: Optional[int]
    N: Optional[int]


class BaseDistribution(ABC):
    @abstractmethod
    def calculate(self, **kwargs: Any) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    def get_probabilities(self, **kwargs: Any) -> Tuple[List[int], List[float]]:
        pass
    
    @abstractmethod
    def get_statistics(self, **kwargs: Any) -> Dict[str, Any]:
        pass
    
    @classmethod
    def get_name(cls) -> str:
        return cls.__name__.replace('Distribution', '')


class BinomialDistribution(BaseDistribution):
    def __init__(self) -> None:
        self.n: Optional[int] = None
        self.p: Optional[float] = None
        self.x: Optional[int] = None
        self.N: Optional[int] = None
        self.is_finite: bool = False
    
    def _validate_inputs(self, n: int, p: float, x: Optional[int] = None, N: Optional[int] = None) -> None:
        if n <= 0:
            raise ValueError("El tamaño de la muestra (n) debe ser mayor que 0")
        if not 0 <= p <= 1:
            raise ValueError("La probabilidad (p) debe estar entre 0 y 1")
        if x is not None and (x < 0 or x > n):
            raise ValueError(f"El número de éxitos (x) debe estar entre 0 y {n}")
        if N is not None and N <= 0:
            raise ValueError("El tamaño de la población (N) debe ser mayor que 0")
        if N is not None and n > N:
            raise ValueError("El tamaño de la muestra (n) no puede ser mayor que la población (N)")
    
    def _determine_population_type(self, n: int, N: Optional[int]) -> Tuple[bool, Optional[float]]:
        if N is None:
            return False, None
        
        ratio = n / N
        if ratio > 0.05:
            return True, ratio
        return False, ratio
    
    def _calculate_correction_factor(self, n: int, N: int) -> float:
        return math.sqrt((N - n) / (N - 1))
    
    def calculate_probability(self, n: int, p: float, x: int) -> float:
        return float(stats.binom.pmf(x, n, p))
    
    def calculate_mean(self, n: int, p: float) -> float:
        return n * p
    
    def calculate_variance(self, n: int, p: float) -> float:
        return n * p * (1 - p)
    
    def calculate_std(self, n: int, p: float, N: Optional[int] = None) -> Tuple[float, Optional[float]]:
        variance = self.calculate_variance(n, p)
        std = math.sqrt(variance)
        
        if N is not None and n / N > 0.05:
            correction = self._calculate_correction_factor(n, N)
            adjusted_std = std * correction
            return std, adjusted_std
        
        return std, None
    
    def calculate_skewness(self, n: int, p: float) -> float:
        q = 1 - p
        if p == 0 or p == 1:
            return 0
        return (1 - 2 * p) / math.sqrt(n * p * q)
    
    def calculate_kurtosis(self, n: int, p: float) -> float:
        q = 1 - p
        if p == 0 or p == 1:
            return 0
        return (1 - 6 * p * q) / (n * p * q)
    
    def interpret_skewness(self, skewness: float) -> str:
        if skewness < -0.5:
            return "Asimetría negativa significativa: La distribución tiene una cola más larga hacia la izquierda."
        elif skewness > 0.5:
            return "Asimetría positiva significativa: La distribución tiene una cola más larga hacia la derecha."
        elif -0.5 <= skewness <= 0.5:
            if abs(skewness) < 0.1:
                return "Distribución aproximadamente simétrica."
            elif skewness < 0:
                return "Ligera asimetría negativa: La distribución tiende a inclinarse hacia la izquierda."
            else:
                return "Ligera asimetría positiva: La distribución tiende a inclinarse hacia la derecha."
        return "Simétrica"
    
    def interpret_kurtosis(self, kurtosis: float) -> str:
        if kurtosis > 1:
            return "Leptocúrtica: La distribución es más puntiaguda que una distribución normal (colas pesadas)."
        elif kurtosis < -1:
            return "Platicúrtica: La distribución es más plana que una distribución normal (colas ligeras)."
        else:
            return "Mesocúrtica: La distribución tiene una forma similar a la campana de Gauss."
    
    def calculate(self, **kwargs: Any) -> Dict[str, Any]:
        n: int = kwargs.get('n')
        p: float = kwargs.get('p')
        x: Optional[int] = kwargs.get('x')
        N: Optional[int] = kwargs.get('N')
        
        self._validate_inputs(n, p, x, N)
        
        self.n = n
        self.p = p
        self.x = x
        self.N = N
        
        self.is_finite, ratio = self._determine_population_type(n, N)
        
        mean = self.calculate_mean(n, p)
        std, adjusted_std = self.calculate_std(n, p, N)
        skewness = self.calculate_skewness(n, p)
        kurtosis = self.calculate_kurtosis(n, p)
        
        result: Dict[str, Any] = {
            'inputs': {
                'n': n,
                'p': p,
                'x': x,
                'N': N,
            },
            'population_type': 'Finita' if self.is_finite else 'Infinita',
            'population_ratio': ratio,
            'statistics': {
                'mean': round(mean, 6),
                'variance': round(self.calculate_variance(n, p), 6),
                'std': round(std, 6),
                'adjusted_std': round(adjusted_std, 6) if adjusted_std else None,
                'correction_factor': round(self._calculate_correction_factor(n, N), 6) if self.is_finite and N else None,
                'skewness': round(skewness, 6),
                'kurtosis': round(kurtosis, 6),
            },
            'interpretations': {
                'skewness': self.interpret_skewness(skewness),
                'kurtosis': self.interpret_kurtosis(kurtosis),
            },
        }
        
        if x is not None:
            result['probability_x'] = round(self.calculate_probability(n, p, x), 6)
            result['probability_x_pct'] = round(self.calculate_probability(n, p, x) * 100, 4)
        
        return result
    
    def get_probabilities(self, **kwargs: Any) -> Tuple[List[int], List[float]]:
        n: int = kwargs.get('n')
        p: float = kwargs.get('p')
        
        x_values = list(range(n + 1))
        probabilities = [round(self.calculate_probability(n, p, x) * 100, 4) for x in x_values]
        return x_values, probabilities
    
    def get_statistics(self, **kwargs: Any) -> Dict[str, Any]:
        n: int = kwargs.get('n')
        p: float = kwargs.get('p')
        N: Optional[int] = kwargs.get('N')
        
        mean = self.calculate_mean(n, p)
        std, adjusted_std = self.calculate_std(n, p, N)
        skewness = self.calculate_skewness(n, p)
        kurtosis = self.calculate_kurtosis(n, p)
        
        return {
            'mean': round(mean, 6),
            'std': round(std, 6),
            'adjusted_std': round(adjusted_std, 6) if adjusted_std else None,
            'skewness': round(skewness, 6),
            'kurtosis': round(kurtosis, 6),
        }


class HypergeometricParams(TypedDict, total=False):
    N: int
    K: int
    n: int
    x: Optional[int]


class HypergeometricDistribution(BaseDistribution):
    def __init__(self) -> None:
        self.N: Optional[int] = None
        self.K: Optional[int] = None
        self.n: Optional[int] = None
        self.x: Optional[int] = None
    
    def _validate_inputs(self, N: int, K: int, n: int, x: Optional[int] = None) -> None:
        if N <= 0:
            raise ValueError("El tamaño de la población (N) debe ser mayor que 0")
        if K < 0:
            raise ValueError("El número de éxitos en la población (K) no puede ser negativo")
        if K > N:
            raise ValueError("El número de éxitos en la población (K) no puede ser mayor que N")
        if n <= 0:
            raise ValueError("El tamaño de la muestra (n) debe ser mayor que 0")
        if n > N:
            raise ValueError("El tamaño de la muestra (n) no puede ser mayor que la población (N)")
        if x is not None:
            if x < 0:
                raise ValueError("El número de éxitos en la muestra (x) no puede ser negativo")
            if x > n:
                raise ValueError(f"El número de éxitos en la muestra (x) no puede ser mayor que {n}")
            if x > K:
                raise ValueError(f"El número de éxitos en la muestra (x) no puede ser mayor que K={K}")
    
    def calculate_probability(self, N: int, K: int, n: int, x: int) -> float:
        return float(stats.hypergeom.pmf(x, N, K, n))
    
    def calculate_mean(self, N: int, K: int, n: int) -> float:
        return n * (K / N)
    
    def calculate_variance(self, N: int, K: int, n: int) -> float:
        p = K / N
        q = 1 - p
        return n * p * q * ((N - n) / (N - 1))
    
    def calculate_std(self, N: int, K: int, n: int) -> float:
        variance = self.calculate_variance(N, K, n)
        return math.sqrt(variance)
    
    def calculate_skewness(self, N: int, K: int, n: int) -> float:
        if N == 1:
            return 0
        p = K / N
        q = 1 - p
        numerator = (N - 2 * K) * math.sqrt(N - 1) * (N - 2 * n)
        denominator = math.sqrt(n * K * (N - K) * (N - n)) * (N - 2)
        if denominator == 0:
            return 0
        return numerator / denominator
    
    def calculate_kurtosis(self, N: int, K: int, n: int) -> float:
        if N <= 3:
            return 0
        p = K / N
        q = 1 - p
        
        term1 = (N - 1) * (N * (N + 1) - 6 * K * (N - K) * (N - n) / (n * (N - n)))
        term2 = 3 * n * K * (N - K) * (N - n) / (n * (N - n))
        numerator = term1 - term2
        
        denominator = n * K * (N - K) * (N - n) * (N - 2) * (N - 3) / (N - 1)
        if denominator == 0:
            return 0
        
        excess_kurtosis = (N + 1) * numerator / denominator
        return excess_kurtosis
    
    def calculate_median(self, N: int, K: int, n: int) -> int:
        mean = self.calculate_mean(N, K, n)
        floor_mean = int(mean)
        ceil_mean = floor_mean + 1
        
        prob_floor = self.calculate_probability(N, K, n, floor_mean)
        prob_ceil = self.calculate_probability(N, K, n, ceil_mean) if ceil_mean <= min(n, K) else 0
        
        cumulative = 0
        for x in range(min(n, K) + 1):
            cumulative += self.calculate_probability(N, K, n, x)
            if cumulative >= 0.5:
                return x
        return floor_mean
    
    def interpret_skewness_by_median(self, N: int, K: int, n: int) -> Tuple[str, float, float]:
        mean = self.calculate_mean(N, K, n)
        median = self.calculate_median(N, K, n)
        
        if mean < median - 0.1:
            interpretation = "Sesgo Negativo (Asimetría izquierda): La media es menor que la mediana, indicando una cola más larga hacia valores menores."
        elif mean > median + 0.1:
            interpretation = "Sesgo Positivo (Asimetría derecha): La media es mayor que la mediana, indicando una cola más larga hacia valores mayores."
        else:
            interpretation = "Sesgo Nulo (Simétrica): La media y la mediana son aproximadamente iguales, indicando una distribución simétrica."
        
        return interpretation, round(mean, 6), median
    
    def interpret_kurtosis(self, kurtosis: float) -> str:
        if kurtosis > 1:
            return "Leptocúrtica: La distribución es más puntiaguda que una distribución normal (colas pesadas)."
        elif kurtosis < -1:
            return "Platicúrtica: La distribución es más plana que una distribución normal (colas ligeras)."
        else:
            return "Mesocúrtica: La distribución tiene una forma similar a la campana de Gauss."
    
    def calculate(self, **kwargs: Any) -> Dict[str, Any]:
        N: int = kwargs.get('N')
        K: int = kwargs.get('K')
        n: int = kwargs.get('n')
        x: Optional[int] = kwargs.get('x')
        
        self._validate_inputs(N, K, n, x)
        
        self.N = N
        self.K = K
        self.n = n
        self.x = x
        
        p = K / N
        
        mean = self.calculate_mean(N, K, n)
        variance = self.calculate_variance(N, K, n)
        std = self.calculate_std(N, K, n)
        skewness = self.calculate_skewness(N, K, n)
        kurtosis = self.calculate_kurtosis(N, K, n)
        
        skewness_interp, mean_val, median_val = self.interpret_skewness_by_median(N, K, n)
        
        result: Dict[str, Any] = {
            'inputs': {
                'N': N,
                'K': K,
                'n': n,
                'x': x,
                'p': round(p, 6),
            },
            'population_type': 'Finita',
            'sample_ratio': round(n / N, 4),
            'statistics': {
                'mean': round(mean, 6),
                'median': median_val,
                'variance': round(variance, 6),
                'std': round(std, 6),
                'skewness': round(skewness, 6),
                'kurtosis': round(kurtosis, 6),
            },
            'interpretations': {
                'skewness': skewness_interp,
                'kurtosis': self.interpret_kurtosis(kurtosis),
            },
        }
        
        if x is not None:
            result['probability_x'] = round(self.calculate_probability(N, K, n, x), 6)
            result['probability_x_pct'] = round(self.calculate_probability(N, K, n, x) * 100, 4)
        
        return result
    
    def get_probabilities(self, **kwargs: Any) -> Tuple[List[int], List[float]]:
        N: int = kwargs.get('N')
        K: int = kwargs.get('K')
        n: int = kwargs.get('n')
        
        max_x = min(n, K)
        x_values = list(range(max_x + 1))
        probabilities = [round(self.calculate_probability(N, K, n, x) * 100, 4) for x in x_values]
        return x_values, probabilities
    
    def get_statistics(self, **kwargs: Any) -> Dict[str, Any]:
        N: int = kwargs.get('N')
        K: int = kwargs.get('K')
        n: int = kwargs.get('n')
        
        mean = self.calculate_mean(N, K, n)
        std = self.calculate_std(N, K, n)
        skewness = self.calculate_skewness(N, K, n)
        kurtosis = self.calculate_kurtosis(N, K, n)
        _, mean_val, median_val = self.interpret_skewness_by_median(N, K, n)
        
        return {
            'mean': round(mean, 6),
            'median': median_val,
            'std': round(std, 6),
            'skewness': round(skewness, 6),
            'kurtosis': round(kurtosis, 6),
        }


class PoissonParams(TypedDict, total=False):
    lambda_param: float
    x: Optional[int]
    x_min: Optional[int]
    x_max: Optional[int]


class PoissonDistribution(BaseDistribution):
    def __init__(self) -> None:
        self.lambda_param: Optional[float] = None
        self.x: Optional[int] = None
    
    def _validate_inputs(self, lambda_param: float, x: Optional[int] = None) -> None:
        if lambda_param <= 0:
            raise ValueError("El parámetro lambda (λ) debe ser mayor que 0")
        if x is not None and x < 0:
            raise ValueError("El número de eventos (x) no puede ser negativo")
    
    def calculate_probability(self, lambda_param: float, x: int) -> float:
        return float(stats.poisson.pmf(x, lambda_param))
    
    def calculate_mean(self, lambda_param: float) -> float:
        return lambda_param
    
    def calculate_variance(self, lambda_param: float) -> float:
        return lambda_param
    
    def calculate_std(self, lambda_param: float) -> float:
        return math.sqrt(lambda_param)
    
    def calculate_skewness(self, lambda_param: float) -> float:
        return 1 / math.sqrt(lambda_param)
    
    def calculate_kurtosis(self, lambda_param: float) -> float:
        return 1 / lambda_param
    
    def calculate_median(self, lambda_param: float) -> int:
        return int(math.floor(lambda_param + 1/3 - 0.02/lambda_param))
    
    def interpret_skewness(self, skewness: float, mean: float, median: float) -> Tuple[str, str, str]:
        if skewness < -0.5:
            interpretation = "Sesgo negativo significativo: La distribución tiene una cola más larga hacia la izquierda."
            comparison = "Sesgo negativo (media < mediana)"
        elif skewness > 0.5:
            interpretation = "Sesgo positivo significativo: La distribución tiene una cola más larga hacia la derecha."
            comparison = "Sesgo positivo (media > mediana)"
        else:
            interpretation = "Distribución aproximadamente simétrica."
            if abs(mean - median) < 0.01:
                comparison = "Sesgo nulo (media = mediana)"
            elif mean < median:
                comparison = "Sesgo negativo (media < mediana)"
            else:
                comparison = "Sesgo positivo (media > mediana)"
        
        label = "positivo" if skewness > 0.5 else ("negativo" if skewness < -0.5 else "nulo")
        return interpretation, comparison, label
    
    def interpret_kurtosis(self, kurtosis: float) -> Tuple[str, str]:
        if kurtosis < -0.5:
            return "Platicúrtica: La distribución es más plana que una normal (colas ligeras).", "Platicúrtica"
        elif kurtosis > 0.5:
            return "Leptocúrtica: La distribución es más picuda que una normal (colas pesadas).", "Leptocúrtica"
        else:
            return "Mesocúrtica: La distribución tiene forma similar a la campana de Gauss.", "Mesocúrtica (campana de Gauss)"
    
    def calculate(self, **kwargs: Any) -> Dict[str, Any]:
        lambda_param: float = kwargs.get('lambda_param')
        x: Optional[int] = kwargs.get('x')
        x_min: Optional[int] = kwargs.get('x_min')
        x_max: Optional[int] = kwargs.get('x_max')
        
        self._validate_inputs(lambda_param, x)
        
        self.lambda_param = lambda_param
        self.x = x
        
        mean = self.calculate_mean(lambda_param)
        variance = self.calculate_variance(lambda_param)
        std = self.calculate_std(lambda_param)
        skewness = self.calculate_skewness(lambda_param)
        kurtosis = self.calculate_kurtosis(lambda_param)
        median = self.calculate_median(lambda_param)
        
        skewness_interp, skewness_comparison, skewness_label = self.interpret_skewness(skewness, mean, median)
        kurtosis_interp, kurtosis_label = self.interpret_kurtosis(kurtosis)
        
        probability_x = None
        probability_x_pct = None
        cumulative_prob_x = None
        range_probabilities = None
        
        if x is not None:
            probability_x = self.calculate_probability(lambda_param, x)
            probability_x_pct = round(probability_x * 100, 6)
            cumulative_prob_x = float(stats.poisson.cdf(x, lambda_param))
            
            range_probs = []
            cum_sum = 0.0
            for i in range(x + 1):
                prob = self.calculate_probability(lambda_param, i)
                cum_sum += prob
                range_probs.append({
                    'x': i,
                    'p': round(prob * 100, 4),
                    'cumulative': round(cum_sum * 100, 4)
                })
            range_probabilities = range_probs
        
        range_probability = None
        range_probability_pct = None
        if x_min is not None and x_max is not None:
            range_probability = float(stats.poisson.cdf(x_max, lambda_param) - stats.poisson.cdf(x_min - 1, lambda_param))
            range_probability_pct = round(range_probability * 100, 4)
        
        result = {
            'inputs': {
                'lambda': round(lambda_param, 6),
                'x': x,
                'x_min': x_min,
                'x_max': x_max,
            },
            'population_type': 'Poisson',
            'statistics': {
                'mean': round(mean, 6),
                'median': median,
                'variance': round(variance, 6),
                'std': round(std, 6),
                'skewness': round(skewness, 6),
                'kurtosis': round(kurtosis, 6),
            },
            'interpretations': {
                'skewness': skewness_interp,
                'skewness_comparison': skewness_comparison,
                'skewness_label': skewness_label,
                'kurtosis': kurtosis_interp,
                'kurtosis_label': kurtosis_label,
            },
            'probability_x': probability_x,
            'probability_x_pct': probability_x_pct,
            'cumulative_prob_x': cumulative_prob_x,
            'range_probabilities': range_probabilities,
            'range_probability_pct': range_probability_pct,
        }
        
        return result
    
    def get_probabilities(self, **kwargs: Any) -> Tuple[List[int], List[float]]:
        lambda_param: float = kwargs.get('lambda_param')
        
        max_x = int(lambda_param + 4 * math.sqrt(lambda_param)) + 1
        max_x = max(max_x, 20)
        
        x_values = list(range(max_x + 1))
        probabilities = [round(self.calculate_probability(lambda_param, x) * 100, 4) for x in x_values]
        return x_values, probabilities
    
    def get_statistics(self, **kwargs: Any) -> Dict[str, Any]:
        lambda_param: float = kwargs.get('lambda_param')
        
        mean = self.calculate_mean(lambda_param)
        std = self.calculate_std(lambda_param)
        skewness = self.calculate_skewness(lambda_param)
        kurtosis = self.calculate_kurtosis(lambda_param)
        median = self.calculate_median(lambda_param)
        
        return {
            'mean': round(mean, 6),
            'median': median,
            'std': round(std, 6),
            'skewness': round(skewness, 6),
            'kurtosis': round(kurtosis, 6),
        }


class DistributionFactory:
    _distributions: Dict[str, type[BaseDistribution]] = {
        'binomial': BinomialDistribution,
        'hypergeometric': HypergeometricDistribution,
        'poisson': PoissonDistribution,
    }
    
    @classmethod
    def register(cls, name: str, distribution_class: type[BaseDistribution]) -> None:
        cls._distributions[name.lower()] = distribution_class
    
    @classmethod
    def create(cls, distribution_type: str) -> BaseDistribution:
        distribution_type = distribution_type.lower()
        if distribution_type not in cls._distributions:
            available = ', '.join(cls._distributions.keys())
            raise ValueError(f"Distribución '{distribution_type}' no disponible. Opciones: {available}")
        return cls._distributions[distribution_type]()
    
    @classmethod
    def get_available_distributions(cls) -> List[str]:
        return list(cls._distributions.keys())
