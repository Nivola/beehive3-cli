# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

from setuptools import setup, find_packages
from beehive3_cli.core.version import get_version

VERSION = get_version()

f = open('README.md', 'r')
LONG_DESCRIPTION = f.read()
f.close()

setup(
    name='beehive3_cli',
    version=VERSION,
    description='Beehive Console',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    author='CSI Piemonte',
    author_email='nivola.engineering@csi.it',
    url='https://gitlab.csi.it/nivola/cmp/beehive3-cli',
    license='GNU General Public License v3.0',
    packages=find_packages(exclude=['ez_setup', 'tests*']),
    package_data={
        'beehive3_cli': ['templates/*', 'VERSION'],
        #'beehive3_cli': ['VERSION']
    },
    include_package_data=True,
    entry_points="""
        [console_scripts]
        beehive = beehive.main:main
    """,
)
