#!/usr/bin/env python
import os
from setuptools import setup, find_packages

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def find_package_data(pkg, filetypes):
    import glob

    out = []
    for f in filetypes:
        for x in range(0, 20):
            pattern = pkg + '/' + ('*/' * x) + f
            out.extend([p[len(pkg)+1:] for p in glob.glob(pattern)])
    return out


setup(
    name = "semanticeditor",
    version = "0.3",
    description = "A Django CMS plugin for editing text with presentation and layout in a semantic way.",
    long_description = (
        read('README.rst') + '\n\n' + read('CHANGES.rst')
        ),
    url = 'https://bitbucket.org/spookylukey/semanticeditor/',
    license = 'BSD',
    author = 'Luke Plant',
    author_email = 'L.Plant.98@cantab.net',
    packages = find_packages(),
    package_data = {
        'semanticeditor': find_package_data('semanticeditor', ['*.js', '*.html', '*.css', '*.png'])
        },
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    install_requires = ['lxml >= 2.2.4',
                        'pyquery >= 0.6.1',
                        'django-cms >= 2.0, < 3',
                        'django-multiselectfield >= 0.0.2',
                        'South>=1.0',
                        'django >= 1.4, < 1.6',
                        ],
)
