# -*- coding: utf-8 -*-
import json
from django.contrib.auth.decorators import login_required
from splunkdj.decorators.render import render_to
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.utils.decorators import available_attrs
from functools import wraps
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import splunklib.client as client
import splunklib.results as results
from django.contrib.auth import authenticate
from datetime import timedelta, date, datetime
from config import CustomConfig
from jose import jws

def require_post_params(params):
    def decorator(func):
        @wraps(func, assigned=available_attrs(func))
        def inner(request, *args, **kwargs):
            if request.method != "OPTIONS" and not all(param in request.POST for param in params):
                return HttpResponseBadRequest()
            return func(request, *args, **kwargs)
        return inner
    return decorator

def cors_response(context):
    response = HttpResponse(json.dumps(context), content_type="application/json")
    response["Access-Control-Allow-Origin"] = CustomConfig.CORS_URL
    response["Access-Control-Allow-Credentials"] = "true"
    response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE,PATCH,OPTIONS"
    return response

def execute_query(query):
    service = client.connect(
        host=CustomConfig.SPLUNK_HOST,
        port=CustomConfig.SPLUNK_PORT,
        username=CustomConfig.SPLUNK_USERNAME,
        password=CustomConfig.SPLUNK_PASSWORD
    )
    kwargs = {"exec_mode": "blocking"}
    job = service.jobs.create(query, **kwargs)
    ret = []
    for result in results.ResultsReader(job.results()):
        ret.append(result)
    job.cancel()
    return ret

@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
@require_post_params(params=['username', 'password'])
def auth_jwt(request):
    username = "admin"
    password = "changeme"
    user = authenticate(username=username, password=password)
    if user == None:
        raise Http404("Invalid username and password")
    expiry = datetime.now() + timedelta(hours=CustomConfig.JWT_EXPIRATION_HOURS)
    token = jws.sign({'username': user.username, 'expiry': expiry.strftime('%Y/%m/%d %H:%M:%S'), 'roles': ["admin"]}, 'seKre8', algorithm='HS256')
    context = {'token': token}
    return cors_response(context)

@render_to('prueba:home.html')
@login_required
def home(request):

    query_1 = """
        | inputlookup traffic_violations.csv
        | rename "Date Of Stop" as fecha "Time Of Stop" as time
        | eval fecha = fecha." ".time
        | eval fecha_epoch = strptime(fecha,"%d/%m/%Y %H:%M:%S")
        $filtro_fecha$
        | rename "Make" as coche
        $filtro_coche$
        | rename "Alcohol" as alcohol
        | where alcohol="Yes"
        | stats count by coche
        | rename coche as "Marca de coche" count as "Positivos en Alcohol"
    """

    query_2 = """
        | inputlookup traffic_violations.csv
        | rename "Make" as coche
        $filtro_coche$
        | rename "Year" as year
        | where year>1900 AND year<2018
        $filtro_anyo$
        | stats count by year
        | rename year as "Año" count as "Num de Infracciones"
    """

    query_2_map = """
        | inputlookup traffic_violations.csv
        | rename "Make" as coche
        $filtro_coche$
        | rename "Year" as year "Latitude" as lat "Longitude" as lon
        | where year>1900 AND year<2018
        $filtro_anyo$
        | geostats count by year
    """


    context = {
        "query_1":query_1,
        "query_2":query_2,
        "query_2_map":query_2_map,

    }

    context = { q: ' '.join( context[q].replace("\n"," ").replace("\t"," ").split()) for q in context }

    return context
