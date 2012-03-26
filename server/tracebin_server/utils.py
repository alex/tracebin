import json

from django.http import HttpResponse


def JSONResponse(data, status_code=200):
    response = HttpResponse(mimetype="application/json", status=status_code)
    json.dump(data, response)
    return response