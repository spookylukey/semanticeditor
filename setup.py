import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "semanticeditor",
    version = "0.1",
    description = "A Django CMS plugin for editing text with presentation and layout in a semantic way.",
    long_description = read('README.rst'),
    url = 'https://bitbucket.org/spookylukey/semanticeditor/',
    license = 'BSD',
    author = 'Luke Plant',
    author_email = 'L.Plant.98@cantab.net',
    packages = find_packages(),
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Framework :: Django',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires = ['lxml >= 2.2.4', 'pyquery >= 0.3.1', 'django-cms >= 2.0'],
)
