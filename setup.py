# coding: utf-8

import os
from setuptools import setup, find_packages


def get_version():
    bd = os.path.dirname(__file__)

    with open(os.path.join(bd, 'yandex_kassa/version.py')) as f:
        version = dict()
        exec(f.read(), version)

        return version['VERSION']


setup(
    name='yandex-kassa',
    version=get_version(),
    author='Konstantin Kruglov',
    author_email='kruglovk@gmail.com',
    description='empty',
    url='https://github.com/k0st1an/yandex-kassa',
    packages=find_packages(),
    # py_modules=['yandex_kassa'],
    license='Apache License Version 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3 :: Only',
        'Operating System :: POSIX :: Linux',
    ],
)
