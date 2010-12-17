Package install
===============

The 'semanticeditor' package must be on your Python path, by whatever
method. (It can be installed from PyPI using easy_install/pip, or use the
setup.py in the downloaded package in the normal way).

Dependencies
============

 * Django, tested with Django 1.1
 * django-cms2, tested on r172 or later
 * lxml, tested with 2.2.4
 * pyquery, tested with 0.3.1
 * Javascript dependencies are included in media/

Settings
========

 * Normal Django settings
 * Normal django-cms2 settings
 * INSTALLED_APPS - add "semanticeditor"
 * SEMANTICEDITOR_MEDIA_URL = os.path.join(MEDIA_URL, "semanticeditor/")

Templates
=========

Automatically found if 'django.template.loaders.app_directories.load_template_source'
is in TEMPLATE_LOADERS.

Media
=====

Media files: media/semanticeditor needs to be copied/linked/served so that it is
under MEDIA_URL.  (i.e. side-by-side with the media/cms directory).

URLS
====

Add the following to the root URL conf::

  (r'^semantic/', include('semanticeditor.urls')),

These are needed for views.

Models
======

Install the models::

  ./manage.py syncdb

Or, if you have South installed (recommended)::

  ./manage.py migrate semanticeditor

