# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='aiorpc',
    version='0.1.2',
    description='A fast RPC library based on asyncio and MessagePack',
    long_description=open('README.rst').read(),
    author='Cholerae Hu',
    author_email='choleraehyq@gmail.com',
    url='http://github.com/choleraehyq/aiorpc',
    packages=find_packages(),
    license=open('LICENSE').read(),
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
