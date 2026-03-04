from typing import Any

from django.test import TestCase
from django.urls import reverse

from services.acceptance_sampling import AcceptanceSamplingService


class AcceptanceSamplingServiceTests(TestCase):
    def test_cumulative_probability_reaches_100_percent(self):
        results = AcceptanceSamplingService.calculate(N=1000, n=25, c=3, p=0.05, limite_tolerancia=95)
        last_row = results['rows'][-1]
        self.assertAlmostEqual(last_row['cumulative_probability'], 100.0, places=3)

    def test_closest_tolerance_index_is_consistent(self):
        tolerance_percent = 65
        results = AcceptanceSamplingService.calculate(N=800, n=20, c=4, p=0.10, limite_tolerancia=tolerance_percent)

        cumulative = [row['cumulative_probability'] / 100 for row in results['rows']]
        expected_index = min(range(len(cumulative)), key=lambda idx: abs(cumulative[idx] - tolerance_percent / 100))
        self.assertEqual(results['closest_tolerance']['index'], expected_index)


class AutoSelectionIntegrationTests(TestCase):
    def test_binomial_page_switches_to_hypergeometric_when_ratio_is_high(self):
        response: Any = self.client.post(
            reverse('distribuciones:binomial'),
            data={
                'N': 100,
                'n': 30,
                'p': 0.2,
                'x': 2,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['results']['model_decision']['distribution_type'], 'hypergeometric')

    def test_hypergeometric_page_switches_to_binomial_when_ratio_is_low(self):
        response: Any = self.client.post(
            reverse('data_manager:hypergeometric'),
            data={
                'N': 1000,
                'K': 80,
                'n': 50,
                'x': 3,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['results']['model_decision']['distribution_type'], 'binomial')
