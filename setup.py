from setuptools import find_packages, setup
from setuptools.command.install import install
from subprocess import check_call

class PreInstallCommand(install):
    def run(self):
        check_call("echo testing...".split())
        install.run(self)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="theticketpost-service",
    version="0.0.1",
    description="A custom newspaper everyday",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/theticketpost/theticketpost-service",
    author="David Antunez, Bruno Cabado, David Maseda",
    author_email="@eipporko, @brunocabado, @wizenink",
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    entry_points={"console_scripts": ["theticketpost-service = theticketpost.app:main"]},
    python_requires=">=3.7",
    install_requires=[
        'flask[async]==2.2.2',
        'aioflask==0.4.0',
        'pyppeteer==1.0.2',
        'bleak==0.19.5',
        'loguru==0.6.0',
        'nest_asyncio==1.5.6',
        'Pillow==9.3.0',
        'schedule==1.1.0',
        'werkzeug==2.2.2',
        'google-api-python-client==2.81.0',
        'google-auth-httplib2==0.1.0',
        'google-auth-oauthlib==1.0.0',
        'google-auth==2.17.3'
    ]
)
