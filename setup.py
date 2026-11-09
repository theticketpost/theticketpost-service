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
    version="1.4.4",
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
    python_requires=">=3.10",
    install_requires=[
        'flask[async]>=3.1,<4',
        'werkzeug>=3.1,<4',
        'pyppeteer>=2.0,<3',
        'bleak>=1.0,<4',
        'loguru>=0.7,<1',
        'Pillow>=11',
        'schedule>=1.2,<2',
        'requests>=2.32,<3',
        'google-api-python-client>=2.150,<3',
        'google-auth-httplib2>=0.2,<1',
        'google-auth-oauthlib>=1.2,<2',
        'google-auth>=2.35,<3',
        'PyGithub>=2.5,<3',
        'packaging>=24'
    ]
)
