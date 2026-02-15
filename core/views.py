from django.shortcuts import render


def home(request):
    context = {
        'page_title': 'Inicio',
        'active_nav': 'home',
    }
    return render(request, 'core/home.html', context)


def about(request):
    context = {
        'page_title': 'Acerca de',
        'active_nav': 'about',
    }
    return render(request, 'core/about.html', context)
