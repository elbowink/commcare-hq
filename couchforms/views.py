from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from couchforms.models import XFormInstance
from couchforms.util import SubmissionPost


@require_POST
@csrf_exempt
def post(request):
    """
    XForms can get posted here.  They will be forwarded to couch.
    
    Just like play, if you specify a callback you get called, 
    otherwise you get a generic response.  Callbacks follow
    a different signature as play, only passing in the document
    (since we don't know what xform was being posted to)
    """
    return SubmissionPost(request).get_response()


def download_form(request, instance_id):
    instance = XFormInstance.get(instance_id) 
    response = HttpResponse(mimetype='application/xml')
    response.write(instance.get_xml())
    # if we want it to download like a file put somethingl like this
    # HttpResponse(mimetype='application/vnd.ms-excel')
    # response['Content-Disposition'] = 'attachment; filename=%s.xml' % instance_id
    return response

def download_attachment(request, instance_id, attachment):
    instance = XFormInstance.get(instance_id)
    attach = instance._attachments[attachment]
    response = HttpResponse(mimetype=attach["content_type"])
    response.write(instance.fetch_attachment(attachment))
    return response