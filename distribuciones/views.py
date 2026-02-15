import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from scipy import stats

from services.distributions import DistributionFactory, BinomialDistribution
from .forms import BinomialDistributionForm


def binomial_view(request):
    form = BinomialDistributionForm()
    results = None
    chart_data = None
    errors = []
    
    if request.method == 'POST':
        form = BinomialDistributionForm(request.POST)
        
        if form.is_valid():
            try:
                n = form.cleaned_data['n']
                p = form.cleaned_data['p']
                x = form.cleaned_data.get('x')
                N = form.cleaned_data.get('N')
                
                distribution = DistributionFactory.create('binomial')
                results = distribution.calculate(n=n, p=p, x=x, N=N)
                
                x_values, probabilities = distribution.get_probabilities(n=n, p=p, N=N)
                
                cumulative_probs = []
                cumulative_sum = 0
                for prob in probabilities:
                    cumulative_sum += prob
                    cumulative_probs.append(round(cumulative_sum, 4))
                
                cumulative_prob_x = None
                if x is not None:
                    cumulative_prob_x = round(float(sum(float(stats.binom.pmf(i, n, p)) for i in range(x + 1)) * 100), 4)
                
                chart_data = {
                    'labels': [f'{i}' for i in x_values],
                    'values': probabilities,
                    'cumulative': cumulative_probs,
                    'x_values': x_values,
                    'x_limit': x,
                    'mean': results['statistics']['mean'],
                    'std': results['statistics']['std'],
                    'cumulative_prob_x': cumulative_prob_x,
                }
                
                if x is not None:
                    results['cumulative_prob_x'] = cumulative_prob_x
                    range_probs = []
                    cum_sum = 0
                    for i in range(x + 1):
                        prob = round(float(stats.binom.pmf(i, n, p)) * 100, 4)
                        cum_sum += prob
                        range_probs.append({
                            'x': i,
                            'p': prob,
                            'cumulative': round(cum_sum, 4)
                        })
                    results['range_probabilities'] = range_probs
                
                messages.success(request, 'Cálculo realizado exitosamente')
                
            except ValueError as e:
                errors.append(str(e))
                messages.error(request, str(e))
            except Exception as e:
                errors.append(f'Error inesperado: {str(e)}')
                messages.error(request, f'Error inesperado: {str(e)}')
        else:
            for field, field_errors in form.errors.items():
                for error in field_errors:
                    errors.append(f'{field}: {error}')
                    messages.error(request, f'{field}: {error}')
    
    context = {
        'form': form,
        'results': results,
        'chart_data': json.dumps(chart_data) if chart_data else None,
        'errors': errors,
        'page_title': 'Distribución Binomial',
        'active_nav': 'binomial',
    }
    
    return render(request, 'distribuciones/binomial.html', context)


@require_http_methods(["GET"])
def available_distributions(request):
    distributions = DistributionFactory.get_available_distributions()
    return JsonResponse({'distributions': distributions})
