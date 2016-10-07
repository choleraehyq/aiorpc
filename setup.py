# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    name='aiorpc',
    version='0.1.0',
    description='A fast RPC library based on asyncio and MessagePack',
    long_description=open('README.md').read(),
    author='Cholerae Hu',
    author_email='choleraehyq@gmail.com',
    url='http://github.com/choleraehyq/aiorpc',
    packages=find_packages(),
    license=open('LICENSE').read(),
    include_package_data=True,
    keywords=['rpc', 'msgpack', 'messagepack', 'msgpackrpc', 'messagepackrpc',
              'messagepack rpc', 'asyncio'],
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: Do What the Fuck You Want to Public License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ),
    install_requires=[
        'msgpack-python',
    ],
    tests_require=[
        'nose',
        'mock',
    ],
    test_suite='nose.collector'
)