from django import forms


class FileUploadForm(forms.Form):
    data_file = forms.FileField(
        label='Archivo de datos',
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'accept': '.xlsx,.xls,.csv',
            'id': 'id_data_file',
        }),
        error_messages={
            'required': 'Debe seleccionar un archivo',
        }
    )


class ColumnSelectionForm(forms.Form):
    column_name = forms.ChoiceField(
        label='Columna para análisis',
        widget=forms.Select(attrs={
            'class': 'input-field',
            'id': 'column-select',
        }),
        error_messages={
            'required': 'Debe seleccionar una columna',
        }
    )
    
    success_category = forms.ChoiceField(
        label='Categoría de éxito',
        widget=forms.Select(attrs={
            'class': 'input-field',
            'id': 'category-select',
        }),
        error_messages={
            'required': 'Debe seleccionar la categoría de éxito',
        }
    )
    
    def __init__(self, *args, **kwargs):
        columns = kwargs.pop('columns', [])
        categories = kwargs.pop('categories', [])
        super().__init__(*args, **kwargs)
        
        if columns:
            self.fields['column_name'].choices = [(col, col) for col in columns]
        
        if categories:
            self.fields['success_category'].choices = [(cat, cat) for cat in categories]


class CalculationParamsForm(forms.Form):
    n = forms.IntegerField(
        label='Tamaño de la muestra (n)',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 50',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe ser al menos 1',
        }
    )
    
    x = forms.IntegerField(
        label='Número de éxitos esperados (x)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Opcional - Ej: 25',
        }),
        error_messages={
            'min_value': 'El valor debe ser al menos 0',
        }
    )
    
    N = forms.IntegerField(
        label='Tamaño de la población (N)',
        required=True,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 100',
            'id': 'population-n',
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe ser al menos 1',
        }
    )
    
    K = forms.IntegerField(
        label='Éxitos en población (K)',
        required=True,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 20',
            'id': 'population-k',
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe ser al menos 0',
        }
    )
    
    def clean(self):
        cleaned_data = super().clean()
        n = cleaned_data.get('n')
        x = cleaned_data.get('x')
        N = cleaned_data.get('N')
        K = cleaned_data.get('K')
        
        if n is not None and x is not None:
            if x < 0 or x > n:
                self.add_error('x', f'El número de éxitos (x) debe estar entre 0 y {n}')
        
        if n is not None and N is not None:
            if n > N:
                self.add_error('n', 'El tamaño de la muestra (n) no puede ser mayor que la población (N)')
        
        if K is not None and N is not None:
            if K > N:
                self.add_error('K', 'K no puede ser mayor que N')
        
        if x is not None and K is not None:
            if x > K:
                self.add_error('x', f'x no puede ser mayor que K={K}')
        
        return cleaned_data


class HypergeometricManualForm(forms.Form):
    N = forms.IntegerField(
        label='Tamaño de la población (N)',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 1000',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe ser al menos 1',
        }
    )
    
    K = forms.IntegerField(
        label='Éxitos en la población (K)',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 200',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe ser al menos 0',
        }
    )
    
    n = forms.IntegerField(
        label='Tamaño de la muestra (n)',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 100',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe ser al menos 1',
        }
    )
    
    x = forms.IntegerField(
        label='Número de éxitos esperados (x)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Opcional - Ej: 20',
        }),
        error_messages={
            'min_value': 'El valor debe ser al menos 0',
        }
    )
    
    def clean(self):
        cleaned_data = super().clean()
        N = cleaned_data.get('N')
        K = cleaned_data.get('K')
        n = cleaned_data.get('n')
        x = cleaned_data.get('x')
        
        if K is not None and N is not None:
            if K > N:
                self.add_error('K', 'K no puede ser mayor que N')
        
        if n is not None and N is not None:
            if n > N:
                self.add_error('n', 'n no puede ser mayor que N')
        
        if x is not None:
            if n is not None and x > n:
                self.add_error('x', f'x no puede ser mayor que n={n}')
            if K is not None and x > K:
                self.add_error('x', f'x no puede ser mayor que K={K}')
        
        return cleaned_data
