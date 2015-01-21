from django.shortcuts import render

from django.http import HttpResponse

def index(request):
    return HttpResponse("Rango says hey there world!")

def about(request):
    return HttpResponse("This tutorial has put together by Stuart Mackle, 2095332")
