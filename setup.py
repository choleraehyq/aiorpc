# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

with open("README.rst", "r") as fh:
    long_description = fh.read()

setup(
    name='aiorpc',
    version='0.1.4',
    description='A fast RPC library based on asyncio and MessagePack',
    long_description_content_type='text/x-rst',
    long_description=long_description,
    author='Cholerae Hu',
    author_email='choleraehyq@gmail.com',
    url='http://github.com/choleraehyq/aiorpc',
    packages=find_packages(),
    license='WTFPL',
    include_package_data=True,
    keywords=['rpc', 'msgpack', 'messagepack', 'msgpackrpc', 'messagepackrpc',
              'asyncio'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
    ],
    install_requires=[
        'msgpack-python',
        'uvloop',
    ],
    tests_require=[
        'nose',
    ],
    test_suite='nose.collector'
)
