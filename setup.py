import os

from setuptools import setup


base_dir = os.path.dirname(__file__)
about = {}
with open(os.path.join(base_dir, "destructify", "__init__.py")) as f:
    exec(f.read(), about)

try:
    long_description = open("README.rst", "r").read()
except Exception:
    long_description = None


setup(
    name='destructify',
    version=about['__version__'],
    packages=['destructify',
              'destructify.fields',
              'destructify.structures'],
    url='https://github.com/ralphje/destructify',
    download_url='https://github.com/ralphje/destructify/tarball/v' + about['__version__'],
    license='MIT',
    author='Ralph Broenink',
    author_email='ralph@ralphbroenink.net',
    description='A Pythonic way to define, parse and modify binary structures',
    long_description=long_description,
    keywords=['struct', 'bytes'],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
