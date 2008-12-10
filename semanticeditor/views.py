from django.http import HttpResponse
from django.utils import simplejson
from django.core.mail import mail_admins
from django.utils.translation import ugettext as _
from semanticeditor.utils import extract_headings, InvalidHtml, IncorrectHeadings, NEWROW_detail, NEWCOL_detail
from semanticeditor.models import CssClass
import sys

def json_view(func):
    """
    Use this decorator on a function that takes a request and returns
    a dictionary of values in order to create a view that handles
    errors and return JSON.

    The dictionary should be in this standard format:

    {'result': 'ok',
     'value': your_actual_value
    }

    or

    {'result': 'error',
     'message': an_error_message
    }
    """
    def wrap(request, *a, **kw):
        response = None
        try:
            response = dict(func(request, *a, **kw))
            if 'result' not in response:
                response['result'] = 'ok'
        except KeyboardInterrupt:
            # Allow keyboard interrupts through for debugging.
            raise
        except Exception, e:
            # Mail the admins with the error
            exc_info = sys.exc_info()
            subject = 'JSON view error: %s' % request.path
            try:
                request_repr = repr(request)
            except:
                request_repr = 'Request repr() unavailable'
            import traceback
            message = 'Traceback:\n%s\n\nRequest:\n%s' % (
                '\n'.join(traceback.format_exception(*exc_info)),
                request_repr,
                )
            mail_admins(subject, message, fail_silently=True)

            # Come what may, we're returning JSON.
            if hasattr(e, 'message'):
                msg = e.message
            else:
                msg = _('Internal error')+': '+str(e)
            response = {'result': 'error',
                        'message': msg}

        json = simplejson.dumps(response)
        return HttpResponse(json, mimetype='application/json')
    return wrap

def failure(msg):
    return dict(result='error', message=msg)

def success(value):
    return dict(result='ok', value=value)

@json_view
def extract_headings_view(request):
    data = request.POST.get('html')
    if data is None:
        return failure("No HTML sent for parsing")

    try:
        headings = extract_headings(data)
    except (InvalidHtml, IncorrectHeadings), e:
        return failure(e.args[0])

    return success(headings)

@json_view
def retrieve_styles(request):
    retval = [NEWROW_detail, NEWCOL_detail]
    retval += [dict(class_name = "class:" + c.class_name,
                    name = c.name,
                    description = c.description)
               for c in CssClass.objects.all()]
    return success(retval)
