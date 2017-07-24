# -*- coding: utf-8 -*-
import json

from django.contrib.auth.decorators import login_required
from splunkdj.decorators.render import render_to
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import splunklib.client as client
import splunklib.results as results

def cors_response(context):
    response = HttpResponse(json.dumps(context), content_type="application/json")
    response["Access-Control-Allow-Origin"] = "http://localhost:3000"
    return response

@require_http_methods(["GET"])
def test_get(request):
    HOST = "localhost"
    PORT = 8089
    USERNAME = "admin"
    PASSWORD = "changeme"

    # Create a Service instance and log in
    service = client.connect(
        host=HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD)

    ret = []
    for app in service.apps:
        ret.append(app.name)

    searchquery_normal = '| inputlookup "traffic_violations.csv" | head 10'
    kwargs_normalsearch = {"exec_mode": "blocking"}
    job = service.jobs.create(searchquery_normal, **kwargs_normalsearch)

    retq = []
    for result in results.ResultsReader(job.results()):
        retq.append(result)

    context = {"Test": "Example get", "Apps": ret, "Job": job.sid, "Count": job.resultCount, "retq": retq}
    return cors_response(context)

@csrf_exempt
@require_http_methods(["POST"])
def test_post(request):
    context = {"Test": "Example post"}
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
