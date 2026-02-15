from django import forms


class BinomialDistributionForm(forms.Form):
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
    
    p = forms.FloatField(
        label='Probabilidad de éxito (p)',
        min_value=0.0,
        max_value=1.0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 0.5',
            'step': '0.0001',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe estar entre 0 y 1',
            'max_value': 'El valor debe estar entre 0 y 1',
        }
    )
    
    x = forms.IntegerField(
        label='Número de éxitos esperados (x)',
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Opcional - Ej: 50',
        }),
        error_messages={
            'min_value': 'El valor debe ser al menos 0',
        }
    )
    
    N = forms.IntegerField(
        label='Tamaño de la población (N)',
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Opcional - Para población finita',
        }),
        error_messages={
            'min_value': 'El valor debe ser al menos 1',
        }
    )
    
    def clean_p(self):
        p = self.cleaned_data.get('p')
        if p is not None:
            p = round(p, 4)
        return p
    
    def clean(self):
        cleaned_data = super().clean()
        n = cleaned_data.get('n')
        x = cleaned_data.get('x')
        N = cleaned_data.get('N')
        
        if n is not None and x is not None:
            if x < 0 or x > n:
                self.add_error('x', f'El número de éxitos (x) debe estar entre 0 y {n}')
        
        if n is not None and N is not None:
            if n > N:
                self.add_error('n', 'El tamaño de la muestra (n) no puede ser mayor que la población (N)')
        
        return cleaned_data
