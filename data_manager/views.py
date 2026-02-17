import json
import io
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from scipy import stats
import pandas as pd

from services.data_processor import DataProcessor, DataProcessingError
from services.model_selector import ModelSelector, DistributionType
from services.distributions import DistributionFactory, HypergeometricDistribution
from .forms import (
    FileUploadForm, 
    ColumnSelectionForm, 
    CalculationParamsForm,
    HypergeometricManualForm
)


def upload_view(request):
    upload_form = FileUploadForm()
    column_form = None
    preview_data = None
    columns_info = None
    file_loaded = False
    analysis = None
    
    if 'dataframe_json' in request.session:
        file_loaded = True
    
    if 'column_analysis' in request.session:
        analysis = request.session['column_analysis']
    
    if request.method == 'POST' and request.FILES.get('data_file'):
        upload_form = FileUploadForm(request.POST, request.FILES)
        
        if upload_form.is_valid():
            data_file = request.FILES['data_file']
            
            is_valid, message = DataProcessor.validate_file(data_file)
            
            if not is_valid:
                messages.error(request, message)
            else:
                try:
                    data_file.seek(0)
                    df = DataProcessor.read_file(data_file)
                    
                    preview_data = DataProcessor.get_preview_data(df)
                    columns_info = DataProcessor.get_columns_info(df)
                    
                    categorical_columns = [
                        col for col, info in columns_info.items() 
                        if info['type'] == 'categorical'
                    ]
                    
                    if not categorical_columns:
                        messages.warning(
                            request, 
                            "No se encontraron columnas categóricas. Solo se mostrarán datos numéricos."
                        )
                    
                    request.session['dataframe_json'] = df.to_json()
                    request.session['columns_info'] = columns_info
                    request.session['preview_data'] = preview_data
                    
                    messages.success(request, f'Archivo cargado: {len(df)} filas, {len(df.columns)} columnas')
                    
                    return redirect('data_manager:upload')
                    
                except DataProcessingError as e:
                    messages.error(request, str(e))
                except Exception as e:
                    messages.error(request, f'Error inesperado: {str(e)}')
    
    if 'columns_info' in request.session:
        columns_info = request.session.get('columns_info')
        preview_data = request.session.get('preview_data')
        
        categorical_columns = [
            col for col, info in columns_info.items() 
            if info['type'] == 'categorical'
        ]
        
        if categorical_columns:
            column_form = ColumnSelectionForm(
                columns=categorical_columns,
                categories=[]
            )
    
    context = {
        'upload_form': upload_form,
        'column_form': column_form,
        'preview_data': preview_data,
        'columns_info': columns_info,
        'file_loaded': file_loaded,
        'analysis': analysis,
        'page_title': 'Gestión de Datos',
        'active_nav': 'data_manager',
    }
    
    return render(request, 'data_manager/upload.html', context)


@require_http_methods(["GET"])
def get_column_categories(request):
    column_name = request.GET.get('column')
    
    if not column_name or 'dataframe_json' not in request.session:
        return JsonResponse({'error': 'Parámetros inválidos'}, status=400)
    
    df = pd.read_json(io.StringIO(request.session['dataframe_json']))
    
    if column_name not in df.columns:
        return JsonResponse({'error': 'Columna no encontrada'}, status=404)
    
    col_data = df[column_name].dropna()
    categories = [str(cat) for cat in col_data.unique()]
    
    return JsonResponse({
        'categories': categories,
        'count': len(categories),
    })


@require_http_methods(["POST"])
def analyze_column(request):
    column_name = request.POST.get('column_name')
    success_category = request.POST.get('success_category')
    
    if not column_name or not success_category:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)
    
    if 'dataframe_json' not in request.session:
        return JsonResponse({'error': 'No hay datos cargados'}, status=400)
    
    try:
        df = pd.read_json(io.StringIO(request.session['dataframe_json']))
        
        analysis = DataProcessor.analyze_categorical_column(df, column_name, success_category)
        
        request.session['column_analysis'] = analysis
        
        return JsonResponse({
            'success': True,
            'analysis': analysis,
        })
        
    except DataProcessingError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


def calculate_auto_view(request):
    results = None
    chart_data = None
    errors = []
    analysis = None
    has_loaded_data = False
    
    if 'column_analysis' in request.session:
        analysis = request.session['column_analysis']
    
    if 'dataframe_json' in request.session:
        has_loaded_data = True
    
    if request.method == 'POST':
        form = CalculationParamsForm(request.POST)
        
        if form.is_valid():
            try:
                n = form.cleaned_data['n']
                x = form.cleaned_data.get('x')
                N = form.cleaned_data.get('N')
                K = form.cleaned_data.get('K')
                
                if N is None or K is None:
                    errors.append('N y K son obligatorios. Si cargó un archivo, debe analizar una columna primero.')
                else:
                    calculation = ModelSelector.calculate_with_auto_selection(N, K, n, x)
                    
                    results = calculation['results']
                    results['model_decision'] = calculation['model_decision']
                    
                    chart_info = calculation['chart_data']
                    
                    cumulative_prob_x = None
                    if x is not None and x < len(chart_info['cumulative']):
                        cumulative_prob_x = chart_info['cumulative'][x]
                        
                        range_probs = []
                        cum_sum = 0
                        for i in range(min(x + 1, len(chart_info['x_values']))):
                            prob = chart_info['probabilities'][i]
                            cum_sum += prob
                            range_probs.append({
                                'x': chart_info['x_values'][i],
                                'p': round(prob, 4),
                                'cumulative': round(cum_sum, 4)
                            })
                        results['range_probabilities'] = range_probs
                    
                    chart_data = {
                        'labels': [str(val) for val in chart_info['x_values']],
                        'values': chart_info['probabilities'],
                        'cumulative': chart_info['cumulative'],
                        'x_values': chart_info['x_values'],
                        'x_limit': x,
                        'mean': results['statistics']['mean'],
                        'std': results['statistics']['std'],
                        'cumulative_prob_x': cumulative_prob_x,
                        'distribution_type': calculation['model_decision']['distribution_type'],
                    }
                    
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
    
    initial_data = {}
    if analysis:
        initial_data['N'] = analysis.get('N')
        initial_data['K'] = analysis.get('K')
    
    form = CalculationParamsForm(initial=initial_data)
    
    context = {
        'form': form,
        'results': results,
        'chart_data': json.dumps(chart_data) if chart_data else None,
        'errors': errors,
        'analysis': analysis,
        'has_loaded_data': has_loaded_data,
        'page_title': 'Cálculo Automático',
        'active_nav': 'data_manager',
    }
    
    return render(request, 'data_manager/calculate_auto.html', context)


def hypergeometric_view(request):
    form = HypergeometricManualForm()
    results = None
    chart_data = None
    errors = []
    
    if request.method == 'POST':
        form = HypergeometricManualForm(request.POST)
        
        if form.is_valid():
            try:
                N = form.cleaned_data['N']
                K = form.cleaned_data['K']
                n = form.cleaned_data['n']
                x = form.cleaned_data.get('x')
                
                distribution = DistributionFactory.create('hypergeometric')
                results = distribution.calculate(N=N, K=K, n=n, x=x)
                
                decision = ModelSelector.decide(N, K, n)
                results['model_decision'] = {
                    'distribution_type': decision.distribution_type.value,
                    'distribution_name': 'Hipergeométrica',
                    'reason': decision.reason,
                    'sample_ratio': decision.sample_ratio,
                    'threshold': decision.threshold_used,
                }
                
                x_values, probabilities = distribution.get_probabilities(N=N, K=K, n=n)
                
                cumulative_probs = []
                cumulative_sum = 0
                for prob in probabilities:
                    cumulative_sum += prob
                    cumulative_probs.append(round(cumulative_sum, 4))
                
                cumulative_prob_x = None
                if x is not None:
                    if x < len(cumulative_probs):
                        cumulative_prob_x = cumulative_probs[x]
                    
                    range_probs = []
                    cum_sum = 0
                    for i in range(min(x + 1, len(x_values))):
                        prob = probabilities[i]
                        cum_sum += prob
                        range_probs.append({
                            'x': x_values[i],
                            'p': round(prob, 4),
                            'cumulative': round(cum_sum, 4)
                        })
                    results['range_probabilities'] = range_probs
                    results['cumulative_prob_x'] = cumulative_prob_x
                
                chart_data = {
                    'labels': [str(val) for val in x_values],
                    'values': probabilities,
                    'cumulative': cumulative_probs,
                    'x_values': x_values,
                    'x_limit': x,
                    'mean': results['statistics']['mean'],
                    'std': results['statistics']['std'],
                    'cumulative_prob_x': cumulative_prob_x,
                }
                
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
        'page_title': 'Distribución Hipergeométrica',
        'active_nav': 'hypergeometric',
    }
    
    return render(request, 'data_manager/hypergeometric.html', context)


def clear_session(request):
    keys_to_clear = ['dataframe_json', 'columns_info', 'preview_data', 'column_analysis']
    for key in keys_to_clear:
        if key in request.session:
            del request.session[key]
    messages.success(request, 'Datos de sesión eliminados')
    return redirect('data_manager:upload')
