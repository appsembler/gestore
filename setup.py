import setuptools

import gestore


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


setuptools.setup(
    name="gestore",
    version=gestore.__version__,
    author="Appsembler",
    author_email="ops@appsembler.com",
    description="Django object management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/appsembler/gestore",
    project_urls={
        "Bug Tracker": "https://github.com/appsembler/gestore/issues",
    },
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Framework :: Django",
        "Framework :: Django :: 1.11",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.0",
        "Framework :: Django :: 3.1",
        "Framework :: Django :: 3.2",
    ],
    python_requires=">=2.7,!=3.0.*,!=3.1.*,!=3.2.*,!=3.3.*,!=3.4.*",
    packages=setuptools.find_packages(
        include=['gestore', 'gestore.*'],
        exclude=['gestore.tests'],
    ),
)
