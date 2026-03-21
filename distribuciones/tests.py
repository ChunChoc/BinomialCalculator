from typing import Any

from django.test import TestCase
from django.urls import reverse

from services.acceptance_sampling import AcceptanceSamplingService
from services.distributions import DistributionFactory, HypergeometricDistribution


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

    def test_acceptance_sampling_comparison_uses_20_percent_rule(self):
        results = AcceptanceSamplingService.calculate(N=100, n=25, c=3, p=0.08, limite_tolerancia=90)

        self.assertEqual(results['model_decision']['distribution_type'], 'hypergeometric')
        self.assertEqual(results['model_decision']['threshold_percent'], 20.0)
        self.assertIn('binomial', results['distribution_comparison'])
        self.assertIn('hypergeometric', results['distribution_comparison'])
        self.assertIn('difference', results['distribution_comparison'])


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


class PoissonToleranceTests(TestCase):
    def test_poisson_distribution_returns_closest_tolerance(self):
        distribution = DistributionFactory.create('poisson')

        results = distribution.calculate(lambda_param=3.2, limite_tolerancia=95)

        self.assertIsNotNone(results['closest_tolerance'])

        closest = results['closest_tolerance']
        expected_x = min(
            range(0, 30),
            key=lambda current_x: abs(closest['tolerance'] - (distribution.calculate(lambda_param=3.2, x=current_x)['cumulative_prob_x'] * 100)),
        )
        self.assertEqual(closest['x'], expected_x)

    def test_poisson_page_accepts_tolerance_input(self):
        response: Any = self.client.post(
            reverse('distribuciones:poisson'),
            data={
                'n': 100,
                'p': 0.02,
                'limite_tolerancia': 90,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.context['results']['closest_tolerance'])


class HypergeometricPoissonComparisonTests(TestCase):
    def test_hypergeometric_distribution_builds_poisson_comparison(self):
        distribution = HypergeometricDistribution()

        comparison = distribution.build_poisson_comparison(N=200, K=8, n=20, x=1)

        self.assertEqual(comparison['lambda'], 0.8)
        self.assertEqual(len(comparison['rows']), 9)
        self.assertIsNotNone(comparison['poisson_probability_x_pct'])

    def test_hypergeometric_page_shows_poisson_comparison(self):
        response: Any = self.client.post(
            reverse('data_manager:hypergeometric'),
            data={
                'N': 200,
                'K': 8,
                'n': 20,
                'x': 1,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('poisson_comparison', response.context['results'])
        self.assertContains(response, 'Comparación Hipergeométrica vs Poisson')
