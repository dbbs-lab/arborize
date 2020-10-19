import setuptools, os

with open(os.path.join(os.path.dirname(__file__), "arborize", "__init__.py"), "r") as f:
    for line in f:
        if "__version__ = " in line:
            exec(line.strip())
            break

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
     name='arborize',
     version=__version__,
     author="Robin De Schepper",
     author_email="robingilbert.deschepper@unipv.it",
     description="Write descriptions for NEURON cell models in an Arbor-like manner.",
     long_description=long_description,
     long_description_content_type="text/markdown",
     url="https://github.com/dbbs-lab/arborize",
     license='GPLv3',
     packages=setuptools.find_packages(),
     classifiers=[
         "Programming Language :: Python :: 3",
         "Operating System :: OS Independent",
     ],
     install_requires=[
        "nrn-glia>=0.3.8",
        "nrn-patch>=3.0.0b0",
        "numpy",
        "errr"
     ],
     extras_require={
      "dev": ["sphinx", "sphinx_rtd_theme"]
     }
 )
