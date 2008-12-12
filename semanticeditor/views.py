from django.http import HttpResponse
from django.utils import simplejson
from django.core.mail import mail_admins
from django.utils.translation import ugettext as _
from semanticeditor.utils import extract_headings, extract_presentation, AllUserErrors, NEWROW, NEWCOL, PresentationClass
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
            response = func(request, *a, **kw)
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
            response = error(msg)

        json = simplejson.dumps(response)
        return HttpResponse(json, mimetype='application/json')
    return wrap

def error(msg):
    """
    Standard error result - for internal errors
    """
    return dict(result='error', message=msg)

def failure(msg):
    """
    Standard failure result
    """
    return dict(result='usererror', message=msg)

def success(value):
    """
    Standard success result
    """
    return dict(result='ok', value=value)


# Anything that depends on values the user may have entered and might
# contain 'errors' should use this, normally passing in AllUserErrors
# as 'exceptions'.
def graceful_errors(exceptions, callback):
    """
    Retrieve a value from a callback, handling the exceptions that
    are passed in, and returning in standard formats
    """
    try:
        val = callback()
    except exceptions, e:
        return failure(e.args[0])
    return success(val)

@json_view
def extract_headings_view(request):
    data = request.POST.get('html')
    if data is None:
        return failure("No HTML sent for parsing")

    return graceful_errors(AllUserErrors, lambda: extract_headings(data))

def PI_to_dict(pi):
    """
    Converts a PresentationInfo to a dictionary
    for use client side
    """
    return pi.__dict__

@json_view
def retrieve_styles(request):
    retval = [NEWROW, NEWCOL]
    retval += [PresentationClass(c.name,
                                 verbose_name=c.verbose_name,
                                 description=c.description)
               for c in CssClass.objects.all().order_by('verbose_name')]
    return success(map(PI_to_dict,retval))

@json_view
def separate_presentation(request):
    """
    Returns a JSON object:
     { presentation: <dictionary of presentation info from html>
       html: <input html stripped of presentation>
     }
    """
    data = request.POST.get('html')
    if data is None:
        return failure("No HTML sent for parsing")

    def _ret():
        pres, html = extract_presentation(data)
        # Rewrite pres so that we can serialise it
        pres2 = {}
        for k, v in pres.items():
            pres2[k] = list(v)
        return dict(presentation=pres2,
                    html=html)

    return graceful_errors(AllUserErrors, _ret)
