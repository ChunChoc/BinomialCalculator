from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class MM1Calculator:
    arrival_rate: float
    service_rate: float
    n_clients: int

    def __post_init__(self) -> None:
        self._validate_inputs()

    def _validate_inputs(self) -> None:
        if self.arrival_rate < 0:
            raise ValueError('La tasa de llegada (lambda) no puede ser negativa')
        if self.service_rate <= 0:
            raise ValueError('La tasa de servicio (mu) debe ser mayor que 0')
        if self.n_clients < 0:
            raise ValueError('El numero de clientes (n) no puede ser negativo')
        if self.service_rate <= self.arrival_rate:
            raise ValueError(
                'La tasa de servicio (mu) debe ser mayor que la tasa de llegada (lambda) para que el sistema sea estable'
            )

    @property
    def utilization(self) -> float:
        return self.arrival_rate / self.service_rate

    @property
    def idle_probability(self) -> float:
        return 1 - self.utilization

    @property
    def queue_length(self) -> float:
        return (self.arrival_rate ** 2) / (self.service_rate * (self.service_rate - self.arrival_rate))

    @property
    def system_length(self) -> float:
        return self.arrival_rate / (self.service_rate - self.arrival_rate)

    @property
    def queue_waiting_time(self) -> float:
        return self.arrival_rate / (self.service_rate * (self.service_rate - self.arrival_rate))

    @property
    def system_waiting_time(self) -> float:
        return 1 / (self.service_rate - self.arrival_rate)

    def probability_n(self, n_clients: Optional[int] = None) -> float:
        state = self.n_clients if n_clients is None else n_clients
        if state < 0:
            raise ValueError('El numero de clientes (n) no puede ser negativo')
        return self.idle_probability * (self.utilization ** state)

    def _round(self, value: float, decimals: int = 6) -> float:
        return round(value, decimals)

    def _utilization_label(self) -> str:
        rho = self.utilization
        if rho < 0.5:
            return 'Baja ocupacion'
        if rho < 0.8:
            return 'Ocupacion moderada'
        return 'Alta ocupacion'

    def _recommendation(self) -> str:
        rho = self.utilization
        if rho < 0.5:
            return 'El sistema tiene suficiente capacidad y bajas esperas promedio.'
        if rho < 0.8:
            return 'El sistema es estable, pero conviene vigilar incrementos en la tasa de llegada.'
        return 'El sistema sigue siendo estable, aunque esta cerca de saturarse y las esperas crecen con rapidez.'

    def calculate(self) -> Dict[str, Any]:
        rho = self.utilization
        p0 = self.idle_probability
        lq = self.queue_length
        ls = self.system_length
        wq = self.queue_waiting_time
        ws = self.system_waiting_time
        pn = self.probability_n()

        return {
            'inputs': {
                'arrival_rate': self._round(self.arrival_rate),
                'service_rate': self._round(self.service_rate),
                'n_clients': self.n_clients,
            },
            'metrics': {
                'rho': self._round(rho),
                'rho_pct': self._round(rho * 100, 4),
                'p0': self._round(p0),
                'p0_pct': self._round(p0 * 100, 4),
                'lq': self._round(lq),
                'ls': self._round(ls),
                'wq': self._round(wq),
                'ws': self._round(ws),
                'pn': self._round(pn),
                'pn_pct': self._round(pn * 100, 4),
                'mu_minus_lambda': self._round(self.service_rate - self.arrival_rate),
            },
            'interpretation': {
                'utilization_level': self._utilization_label(),
                'recommendation': self._recommendation(),
            },
        }

    def _resolve_probability_upper_bound(self, upper_bound: Optional[int] = None) -> int:
        if upper_bound is not None:
            return max(10, upper_bound)

        bound = max(10, self.n_clients)
        cumulative_probability = sum(self.probability_n(index) for index in range(bound + 1))

        while cumulative_probability < 0.995 and bound < 60:
            bound += 5
            cumulative_probability = sum(self.probability_n(index) for index in range(bound + 1))

        return bound

    def build_probability_chart(self, upper_bound: Optional[int] = None) -> Dict[str, Any]:
        max_state = self._resolve_probability_upper_bound(upper_bound)
        labels = [str(index) for index in range(max_state + 1)]
        probabilities = [self._round(self.probability_n(index) * 100, 4) for index in range(max_state + 1)]

        return {
            'labels': labels,
            'probabilities': probabilities,
            'selected_index': self.n_clients,
            'selected_probability': self._round(self.probability_n() * 100, 4),
        }

    def build_congestion_chart(self) -> Dict[str, Any]:
        base_utilizations = [0.0] + [step / 10 for step in range(1, 10)]
        current_utilization = self._round(self.utilization, 4)
        utilization_values = sorted(set(base_utilizations + [current_utilization]))

        labels: List[str] = []
        lambda_values: List[float] = []
        queue_lengths: List[float] = []
        system_lengths: List[float] = []

        for utilization in utilization_values:
            lambda_value = utilization * self.service_rate
            labels.append(f'{utilization * 100:.1f}%')
            lambda_values.append(self._round(lambda_value, 4))

            if utilization == 0:
                queue_lengths.append(0.0)
                system_lengths.append(0.0)
                continue

            lq = (lambda_value ** 2) / (self.service_rate * (self.service_rate - lambda_value))
            ls = lambda_value / (self.service_rate - lambda_value)
            queue_lengths.append(self._round(lq, 4))
            system_lengths.append(self._round(ls, 4))

        return {
            'labels': labels,
            'lambda_values': lambda_values,
            'queue_lengths': queue_lengths,
            'system_lengths': system_lengths,
            'current_index': utilization_values.index(current_utilization),
            'service_rate': self._round(self.service_rate, 4),
        }
