from django.http import HttpResponse
from django.utils import simplejson
from django.core.mail import mail_admins
from django.utils.translation import ugettext as _
from semanticeditor.utils import extract_headings, extract_presentation, format_html, preview_html, AllUserErrors, NEWROW, NEWCOL, PresentationInfo, PresentationClass
from semanticeditor.models import CssClass
import sys
try:
    from functools import wraps
except ImportError:
    from django.utils.functional import wraps  # Python 2.3, 2.4 fallback.


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

    {'result': 'usererror',
     'message': an_error_message

    or

    {'result': 'error',
     'message': an_error_message
    }
    """
    def wrapper(request, *a, **kw):
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
                msg = _('Internal error')+': '+ str(e)
            response = error(msg)

        json = simplejson.dumps(response)
        return HttpResponse(json, mimetype='application/json')

    return wraps(func)(wrapper)

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
# as 'exceptions'.  'server' errors are handled by @json_view
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
    data = request.POST.get('html','').encode("utf-8")
    return graceful_errors(AllUserErrors, lambda: extract_headings(data))

def PI_to_dict(pi):
    """
    Converts a PresentationInfo to a dictionary
    for use client side
    """
    return pi.__dict__

def dict_to_PI(d):
    return PresentationInfo(prestype=d['prestype'], name=d['name'])

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
    data = request.POST.get('html','').encode("utf-8")

    def _handled():
        pres, html = extract_presentation(data)
        # Rewrite pres so that we can serialise it to JSON
        pres2 = {}
        for k, v in pres.items():
            pres2[k] = [PI_to_dict(p) for p in v]
        return dict(presentation=pres2,
                    html=html)

    return graceful_errors(AllUserErrors, _handled)

def _convert_pres(pres):
    # Convert dictionaries into PresentationInfo classes
    for k, v in pres.items():
        # v is list of PI dicts
        for i, item in enumerate(v):
            v[i] = dict_to_PI(item)

@json_view
def combine_presentation(request):
    """
    Combines submitted 'html' and 'presentation' data,
    returning a dictionary containg { html: <combined html> }
    """
    html = request.POST.get('html', '').encode("utf-8")
    presentation = request.POST.get('presentation', '{}')
    presentation = simplejson.loads(presentation)
    _convert_pres(presentation)

    return graceful_errors(AllUserErrors, lambda: dict(html=format_html(html, presentation)))

@json_view
def preview(request):
    html = request.POST.get('html', '').encode("utf-8")
    presentation = request.POST.get('presentation', '{}')
    presentation = simplejson.loads(presentation)
    _convert_pres(presentation)

    return graceful_errors(AllUserErrors, lambda: dict(html=preview_html(html, presentation)))
