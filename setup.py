from setuptools import find_packages, setup

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
        'flask',
    ],
)
