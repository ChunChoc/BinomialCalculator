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

    x_min = forms.IntegerField(
        label='Éxitos mínimos (x_min)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Opcional - Ej: 10',
        }),
        error_messages={
            'min_value': 'El valor debe ser al menos 0',
        }
    )

    x_max = forms.IntegerField(
        label='Éxitos máximos (x_max)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Opcional - Ej: 20',
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
        x_min = cleaned_data.get('x_min')
        x_max = cleaned_data.get('x_max')
        N = cleaned_data.get('N')
        
        if n is not None and x is not None:
            if x < 0 or x > n:
                self.add_error('x', f'El número de éxitos (x) debe estar entre 0 y {n}')

        if n is not None and x_min is not None and x_min > n:
            self.add_error('x_min', f'El valor x_min debe estar entre 0 y {n}')

        if n is not None and x_max is not None and x_max > n:
            self.add_error('x_max', f'El valor x_max debe estar entre 0 y {n}')

        if x_min is not None and x_max is not None and x_min > x_max:
            self.add_error('x_max', 'x_max debe ser mayor o igual que x_min')
        
        if n is not None and N is not None:
            if n > N:
                self.add_error('n', 'El tamaño de la muestra (n) no puede ser mayor que la población (N)')
        
        return cleaned_data


class AcceptanceSamplingForm(forms.Form):
    N = forms.IntegerField(
        label='Tamaño del Lote (N)',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 5000',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe ser al menos 1',
        }
    )

    K = forms.IntegerField(
        label='Defectuosos en el Lote (K)',
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 250',
        }),
        error_messages={
            'min_value': 'El valor debe ser al menos 0',
        }
    )

    n = forms.IntegerField(
        label='Tamaño de la Muestra (n)',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 125',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe ser al menos 1',
        }
    )

    c = forms.IntegerField(
        label='Número de Aceptación (c o X)',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 5',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe ser al menos 0',
        }
    )

    p = forms.FloatField(
        label='Proporción de Defectuosos (p)',
        min_value=0.0,
        max_value=1.0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 0.05',
            'step': '0.0001',
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe estar entre 0 y 1',
            'max_value': 'El valor debe estar entre 0 y 1',
        }
    )

    q = forms.FloatField(
        label='Probabilidad de Fracaso / Proporción de Buenos (q)',
        min_value=0.0,
        max_value=1.0,
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 0.95',
            'step': '0.0001',
        }),
        error_messages={
            'min_value': 'El valor debe estar entre 0 y 1',
            'max_value': 'El valor debe estar entre 0 y 1',
        }
    )

    limite_tolerancia = forms.FloatField(
        label='Límite de Tolerancia a buscar (%)',
        min_value=0.0,
        max_value=100.0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 95',
            'step': '0.01',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El valor debe estar entre 0 y 100',
            'max_value': 'El valor debe estar entre 0 y 100',
        }
    )

    def clean_p(self):
        p = self.cleaned_data.get('p')
        if p is not None:
            return round(p, 6)
        return p

    def clean_limite_tolerancia(self):
        limite_tolerancia = self.cleaned_data.get('limite_tolerancia')
        if limite_tolerancia is not None:
            return round(limite_tolerancia, 4)
        return limite_tolerancia

    def clean(self):
        cleaned_data = super().clean()
        N = cleaned_data.get('N')
        n = cleaned_data.get('n')
        c = cleaned_data.get('c')
        p = cleaned_data.get('p')
        q = cleaned_data.get('q')
        K = cleaned_data.get('K')

        if K is not None and N is not None and K > N:
            self.add_error('K', f'El número de defectuosos (K) no puede ser mayor que el lote (N)')

        if p is None and q is None and K is None:
            self.add_error('p', 'Debe ingresar p, q o K')

        if K is not None and N is not None:
            if p is None:
                cleaned_data['p'] = round(K / N, 6)
                cleaned_data['q'] = round(1 - (K / N), 6)
            else:
                cleaned_data['p'] = round(p, 6)
                cleaned_data['q'] = round(1 - p, 6)
        elif p is None and q is not None:
            cleaned_data['p'] = round(1 - q, 6)
            cleaned_data['q'] = round(q, 6)
        elif p is not None:
            cleaned_data['p'] = round(p, 6)
            cleaned_data['q'] = round(1 - p, 6)

        if N is not None and n is not None and n > N:
            self.add_error('n', 'El tamaño de la muestra (n) no puede ser mayor que el lote (N)')

        if n is not None and c is not None and c > n:
            self.add_error('c', f'El número de aceptación (c) debe estar entre 0 y {n}')

        return cleaned_data


class PoissonDistributionForm(forms.Form):
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
            'placeholder': 'Ej: 0.02',
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
        label='Número de eventos (x)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Opcional - Ej: 3',
        }),
        error_messages={
            'min_value': 'El valor debe ser al menos 0',
        }
    )

    x_min = forms.IntegerField(
        label='Eventos mínimos (x_min)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Opcional - Ej: 2',
        }),
        error_messages={
            'min_value': 'El valor debe ser al menos 0',
        }
    )

    x_max = forms.IntegerField(
        label='Eventos máximos (x_max)',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Opcional - Ej: 5',
        }),
        error_messages={
            'min_value': 'El valor debe ser al menos 0',
        }
    )

    limite_tolerancia = forms.FloatField(
        label='Límite de tolerancia (%)',
        required=False,
        min_value=0.0,
        max_value=100.0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Opcional - Ej: 95',
            'step': '0.01',
        }),
        error_messages={
            'min_value': 'El valor debe estar entre 0 y 100',
            'max_value': 'El valor debe estar entre 0 y 100',
        }
    )
    
    def clean_p(self):
        p = self.cleaned_data.get('p')
        if p is not None:
            p = round(p, 6)
        return p

    def clean_limite_tolerancia(self):
        limite_tolerancia = self.cleaned_data.get('limite_tolerancia')
        if limite_tolerancia is not None:
            return round(limite_tolerancia, 4)
        return limite_tolerancia
    
    def clean(self):
        cleaned_data = super().clean()
        n = cleaned_data.get('n')
        p = cleaned_data.get('p')
        x = cleaned_data.get('x')
        x_min = cleaned_data.get('x_min')
        x_max = cleaned_data.get('x_max')
        
        if x_min is not None and x_max is not None and x_min > x_max:
            self.add_error('x_max', 'x_max debe ser mayor o igual que x_min')
        
        return cleaned_data


class MM1QueueForm(forms.Form):
    arrival_rate = forms.FloatField(
        label='Tasa de llegada (lambda)',
        min_value=0.0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 2.5',
            'step': '0.0001',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'La tasa de llegada no puede ser negativa',
        }
    )

    service_rate = forms.FloatField(
        label='Tasa de servicio (mu)',
        min_value=0.0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 4.0',
            'step': '0.0001',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'La tasa de servicio no puede ser negativa',
        }
    )

    n_clients = forms.IntegerField(
        label='Numero de clientes (n)',
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'input-field',
            'placeholder': 'Ej: 3',
            'required': True,
        }),
        error_messages={
            'required': 'Este campo es obligatorio',
            'min_value': 'El numero de clientes no puede ser negativo',
        }
    )

    def clean_arrival_rate(self):
        arrival_rate = self.cleaned_data.get('arrival_rate')
        if arrival_rate is not None:
            return round(arrival_rate, 6)
        return arrival_rate

    def clean_service_rate(self):
        service_rate = self.cleaned_data.get('service_rate')
        if service_rate is not None:
            return round(service_rate, 6)
        return service_rate

    def clean(self):
        cleaned_data = super().clean()
        arrival_rate = cleaned_data.get('arrival_rate')
        service_rate = cleaned_data.get('service_rate')

        if service_rate is not None and service_rate <= 0:
            self.add_error('service_rate', 'La tasa de servicio (mu) debe ser mayor que 0')

        if arrival_rate is not None and service_rate is not None and service_rate > 0 and service_rate <= arrival_rate:
            self.add_error(
                'service_rate',
                'La tasa de servicio (mu) debe ser mayor que la tasa de llegada (lambda) para que el sistema sea estable',
            )

        return cleaned_data
