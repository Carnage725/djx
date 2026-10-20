from django.http import HttpResponse


def home(request):
    return HttpResponse("djx sandbox")
