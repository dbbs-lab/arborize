import setuptools
import arborize

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
     name='arborize',
     version=arborize.__version__,
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
        "nrn-glia>=0.3.1",
        "nrn-patch>=2.1.1",
        "numpy"
     ],
     extras_require={
      "dev": ["sphinx", "sphinx_rtd_theme"]
     }
 )
