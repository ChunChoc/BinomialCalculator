import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from services.distributions import DistributionFactory
from services.acceptance_sampling import AcceptanceSamplingService
from services.model_selector import ModelSelector, DistributionType
from .forms import BinomialDistributionForm, AcceptanceSamplingForm, PoissonDistributionForm


def binomial_view(request):
    form = BinomialDistributionForm()
    results = None
    chart_data = None
    errors = []
    auto_calculated = False
    
    auto_params = {}
    if request.method == 'GET':
        N_param = request.GET.get('N')
        K_param = request.GET.get('K')
        p_param = request.GET.get('p')
        n_param = request.GET.get('n')
        x_param = request.GET.get('x')
        auto_param = request.GET.get('auto')
        
        if N_param:
            try:
                auto_params['N'] = int(N_param)
            except ValueError:
                pass
        if K_param:
            try:
                auto_params['K'] = int(K_param)
            except ValueError:
                pass
        if p_param:
            try:
                auto_params['p'] = float(p_param)
            except ValueError:
                pass
        if n_param:
            try:
                auto_params['n'] = int(n_param)
            except ValueError:
                pass
        if x_param:
            try:
                auto_params['x'] = int(x_param)
            except ValueError:
                pass
        
        if auto_param == '1' and auto_params.get('n') and (auto_params.get('p') or auto_params.get('K')):
            auto_calculated = True
            post_data = {
                'n': auto_params['n'],
            }
            if auto_params.get('p'):
                post_data['p'] = auto_params['p']
            elif auto_params.get('K') and auto_params.get('N'):
                post_data['p'] = round(auto_params['K'] / auto_params['N'], 6)
            if auto_params.get('x') is not None:
                post_data['x'] = auto_params['x']
            if auto_params.get('N'):
                post_data['N'] = auto_params['N']
            
            form = BinomialDistributionForm(post_data)
            
            if form.is_valid():
                try:
                    n = form.cleaned_data['n']
                    p = form.cleaned_data['p']
                    x = form.cleaned_data.get('x')
                    N = form.cleaned_data.get('N')
                    x_min = form.cleaned_data.get('x_min')
                    x_max = form.cleaned_data.get('x_max')

                    distribution_type = 'binomial'
                    distribution_params = {'n': n, 'p': p, 'x': x, 'N': N}

                    if N is not None:
                        estimated_K = round(N * p)
                        decision = ModelSelector.decide(N=N, K=estimated_K, n=n)

                        if decision.distribution_type == DistributionType.HYPERGEOMETRIC:
                            distribution_type = 'hypergeometric'
                            distribution_params = {'N': N, 'K': estimated_K, 'n': n, 'x': x}

                        results_model_decision = {
                            'distribution_type': decision.distribution_type.value,
                            'distribution_name': 'Hipergeométrica' if decision.distribution_type == DistributionType.HYPERGEOMETRIC else 'Binomial',
                            'reason': decision.reason,
                            'sample_ratio': decision.sample_ratio,
                            'threshold': decision.threshold_used,
                        }
                    else:
                        results_model_decision = None

                    distribution = DistributionFactory.create(distribution_type)
                    results = distribution.calculate(**distribution_params)

                    get_probs_params = {k: v for k, v in distribution_params.items() if k != 'x'}
                    x_values, probabilities = distribution.get_probabilities(**get_probs_params)

                    cumulative_probs = []
                    cumulative_sum = 0.0
                    for prob in probabilities:
                        cumulative_sum += prob
                        cumulative_probs.append(round(cumulative_sum, 4))

                    cumulative_prob_x = None
                    if x is not None and x < len(cumulative_probs):
                        cumulative_prob_x = cumulative_probs[x]

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

                    if results_model_decision:
                        results['model_decision'] = results_model_decision

                    if x_min is not None and x_max is not None:
                        range_probability = 0.0
                        for idx in range(len(x_values)):
                            current_x = x_values[idx]
                            if x_min <= current_x <= x_max:
                                range_probability += probabilities[idx]

                        results['range_bounds'] = {'x_min': x_min, 'x_max': x_max}
                        results['range_probability_pct'] = round(range_probability, 4)

                    if x is not None:
                        results['cumulative_prob_x'] = cumulative_prob_x
                        range_probs = []
                        cum_sum = 0.0
                        upper_limit = min(x + 1, len(x_values))
                        for i in range(upper_limit):
                            prob = probabilities[i]
                            cum_sum += prob
                            range_probs.append({
                                'x': x_values[i],
                                'p': prob,
                                'cumulative': round(cum_sum, 4)
                            })
                        results['range_probabilities'] = range_probs
                    
                    messages.success(request, 'Datos importados y calculados automáticamente desde el archivo.')
                    
                except ValueError as e:
                    errors.append(str(e))
                    messages.error(request, str(e))
                except Exception as e:
                    errors.append(f'Error inesperado: {str(e)}')
                    messages.error(request, f'Error inesperado: {str(e)}')
            else:
                form_errors = form.errors
                if form_errors:
                    for field, field_errors in form_errors.items():
                        for error in field_errors:
                            errors.append(f'{field}: {error}')
                            messages.error(request, f'{field}: {error}')
                form = BinomialDistributionForm(initial=auto_params)
        elif auto_params:
            form = BinomialDistributionForm(initial=auto_params)
    
    if request.method == 'POST' and not auto_calculated:
        form = BinomialDistributionForm(request.POST)
        
        if form.is_valid():
            try:
                n = form.cleaned_data['n']
                p = form.cleaned_data['p']
                x = form.cleaned_data.get('x')
                N = form.cleaned_data.get('N')
                x_min = form.cleaned_data.get('x_min')
                x_max = form.cleaned_data.get('x_max')

                distribution_type = 'binomial'
                distribution_params = {'n': n, 'p': p, 'x': x, 'N': N}

                if N is not None:
                    estimated_K = round(N * p)
                    decision = ModelSelector.decide(N=N, K=estimated_K, n=n)

                    if decision.distribution_type == DistributionType.HYPERGEOMETRIC:
                        distribution_type = 'hypergeometric'
                        distribution_params = {'N': N, 'K': estimated_K, 'n': n, 'x': x}

                    results_model_decision = {
                        'distribution_type': decision.distribution_type.value,
                        'distribution_name': 'Hipergeométrica' if decision.distribution_type == DistributionType.HYPERGEOMETRIC else 'Binomial',
                        'reason': decision.reason,
                        'sample_ratio': decision.sample_ratio,
                        'threshold': decision.threshold_used,
                    }
                else:
                    results_model_decision = None

                distribution = DistributionFactory.create(distribution_type)
                results = distribution.calculate(**distribution_params)

                get_probs_params = {k: v for k, v in distribution_params.items() if k != 'x'}
                x_values, probabilities = distribution.get_probabilities(**get_probs_params)

                cumulative_probs = []
                cumulative_sum = 0.0
                for prob in probabilities:
                    cumulative_sum += prob
                    cumulative_probs.append(round(cumulative_sum, 4))

                cumulative_prob_x = None
                if x is not None and x < len(cumulative_probs):
                    cumulative_prob_x = cumulative_probs[x]

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

                if results_model_decision:
                    results['model_decision'] = results_model_decision

                if x_min is not None and x_max is not None:
                    range_probability = 0.0
                    for idx in range(len(x_values)):
                        current_x = x_values[idx]
                        if x_min <= current_x <= x_max:
                            range_probability += probabilities[idx]

                    results['range_bounds'] = {'x_min': x_min, 'x_max': x_max}
                    results['range_probability_pct'] = round(range_probability, 4)

                if x is not None:
                    results['cumulative_prob_x'] = cumulative_prob_x
                    range_probs = []
                    cum_sum = 0.0
                    upper_limit = min(x + 1, len(x_values))
                    for i in range(upper_limit):
                        prob = probabilities[i]
                        cum_sum += prob
                        range_probs.append({
                            'x': x_values[i],
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
            form_errors = form.errors
            if form_errors:
                for field, field_errors in form_errors.items():
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
        'auto_calculated': auto_calculated,
    }
    
    return render(request, 'distribuciones/binomial.html', context)


@require_http_methods(["GET"])
def available_distributions(request):
    distributions = DistributionFactory.get_available_distributions()
    return JsonResponse({'distributions': distributions})


def acceptance_sampling_view(request):
    form = AcceptanceSamplingForm()
    results = None
    chart_data = None
    errors = []

    if request.method == 'POST':
        form = AcceptanceSamplingForm(request.POST)

        if form.is_valid():
            try:
                N = form.cleaned_data['N']
                n = form.cleaned_data['n']
                c = form.cleaned_data['c']
                p = form.cleaned_data['p']
                K = form.cleaned_data.get('K')
                limite_tolerancia = form.cleaned_data['limite_tolerancia']

                results = AcceptanceSamplingService.calculate(
                    N=N,
                    n=n,
                    c=c,
                    p=p,
                    K=K,
                    limite_tolerancia=limite_tolerancia,
                )

                chart_data = results['chart_data']
                messages.success(request, 'Cálculo de aceptación de lotes realizado exitosamente')

            except ValueError as e:
                errors.append(str(e))
                messages.error(request, str(e))
            except Exception as e:
                errors.append(f'Error inesperado: {str(e)}')
                messages.error(request, f'Error inesperado: {str(e)}')
        else:
            form_errors = form.errors
            if form_errors:
                for field, field_errors in form_errors.items():
                    for error in field_errors:
                        errors.append(f'{field}: {error}')
                        messages.error(request, f'{field}: {error}')

    context = {
        'form': form,
        'results': results,
        'chart_data': json.dumps(chart_data) if chart_data else None,
        'rows_json': json.dumps(results['rows']) if results else None,
        'errors': errors,
        'page_title': 'Muestreo para Aceptación de Lotes',
        'active_nav': 'acceptance_sampling',
    }

    return render(request, 'distribuciones/acceptance_sampling.html', context)


def poisson_view(request):
    form = PoissonDistributionForm()
    results = None
    chart_data = None
    errors = []
    auto_calculated = False
    redirect_to_binomial = False
    redirect_params = {}
    
    auto_params = {}
    if request.method == 'GET':
        n_param = request.GET.get('n')
        p_param = request.GET.get('p')
        x_param = request.GET.get('x')
        auto_param = request.GET.get('auto')
        
        if n_param:
            try:
                auto_params['n'] = int(n_param)
            except ValueError:
                pass
        if p_param:
            try:
                auto_params['p'] = float(p_param)
            except ValueError:
                pass
        if x_param:
            try:
                auto_params['x'] = int(x_param)
            except ValueError:
                pass
        
        if auto_param == '1' and auto_params.get('n') and auto_params.get('p'):
            auto_calculated = True
            form = PoissonDistributionForm(auto_params)
        elif auto_params:
            form = PoissonDistributionForm(initial=auto_params)
    
    if request.method == 'POST' and not auto_calculated:
        form = PoissonDistributionForm(request.POST)
        
        if form.is_valid():
            try:
                n = form.cleaned_data['n']
                p = form.cleaned_data['p']
                x = form.cleaned_data.get('x')
                x_min = form.cleaned_data.get('x_min')
                x_max = form.cleaned_data.get('x_max')
                
                mean = n * p
                
                if p >= 0.10 or mean >= 10:
                    redirect_to_binomial = True
                    redirect_params = {
                        'n': n,
                        'p': p,
                        'x': x if x is not None else '',
                        'auto': '1'
                    }
                    errors.append('redirect_binomial')
                else:
                    lambda_param = mean
                    
                    distribution = DistributionFactory.create('poisson')
                    results = distribution.calculate(
                        lambda_param=lambda_param,
                        x=x,
                        x_min=x_min,
                        x_max=x_max
                    )
                    
                    get_probs_params = {'lambda_param': lambda_param}
                    x_values, probabilities = distribution.get_probabilities(**get_probs_params)
                    
                    cumulative_probs = []
                    cumulative_sum = 0.0
                    for prob in probabilities:
                        cumulative_sum += prob
                        cumulative_probs.append(round(cumulative_sum, 4))
                    
                    cumulative_prob_x = None
                    if x is not None and x < len(cumulative_probs):
                        cumulative_prob_x = cumulative_probs[x]
                    
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
                    
                    messages.success(request, 'Cálculo de distribución Poisson realizado exitosamente')
                    
            except ValueError as e:
                errors.append(str(e))
                messages.error(request, str(e))
            except Exception as e:
                errors.append(f'Error inesperado: {str(e)}')
                messages.error(request, f'Error inesperado: {str(e)}')
        else:
            form_errors = form.errors
            if form_errors:
                for field, field_errors in form_errors.items():
                    for error in field_errors:
                        errors.append(f'{field}: {error}')
                        messages.error(request, f'{field}: {error}')
    
    context = {
        'form': form,
        'results': results,
        'chart_data': json.dumps(chart_data) if chart_data else None,
        'errors': errors,
        'page_title': 'Distribución de Poisson',
        'active_nav': 'poisson',
        'auto_calculated': auto_calculated,
        'redirect_to_binomial': redirect_to_binomial,
        'redirect_params': redirect_params,
    }
    
    return render(request, 'distribuciones/poisson.html', context)
