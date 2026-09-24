import functions_framework

@functions_framework.http
def hello_world(request):
    return "Hello World!"