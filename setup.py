import setuptools, os

with open(os.path.join(os.path.dirname(__file__), "arborize", "__init__.py"), "r") as f:
    for line in f:
        if "__version__ = " in line:
            exec(line.strip())
            break

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="arborize",
    version=__version__,
    author="Robin De Schepper",
    author_email="robingilbert.deschepper@unipv.it",
    description="Write descriptions for NEURON cell models in an Arbor-like manner.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/dbbs-lab/arborize",
    license="GPLv3",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    install_requires=["numpy", "errr>=1.2.0", "morphio>=3.3.3"],
    extras_require={
        "neuron": ["nrn-patch==4.0.0a1", "nrn-glia[neuron]==4.0.0a1"],
        "arbor": ["arbor>=0.8"],
        "dev": ["sphinx", "sphinx_rtd_theme"],
    },
)
