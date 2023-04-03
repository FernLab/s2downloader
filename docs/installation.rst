.. _installation:

============
Installation
============


Using Anaconda or Miniconda (recommended)
-----------------------------------------

Using conda_ (latest version recommended), S2Downloader is installed as follows:


1. Create virtual environment for s2downloader (optional but recommended):

   .. code-block:: bash

    $ conda create -c conda-forge --name s2downloader python=3
    $ conda activate s2downloader


2. Then clone the S2Downloader source code and install S2Downloader and all dependencies from the environment_s2downloader.yml file:

   .. code-block:: bash

    $ git clone git@git.gfz-potsdam.de:fernlab/products/data-portal/s2downloader.git
    $ cd s2downloader
    $ conda env update -n s2downloader -f tests/CI_docker/context/environment_s2downloader.yml
    $ pip install .


This is the preferred method to install S2Downloader, as it always installs the most recent stable release and
automatically resolves all the dependencies.


Using pip (not recommended)
---------------------------

It is also possible to instal S2Downloader via `pip`_. However, please note that S2Downloader depends on some
open source packages that may cause problems when installed with pip. Therefore, we strongly recommend
to resolve the following dependencies before the pip installer is run:

    * TODO


Then, the pip installer can be run by:

   .. code-block:: bash

    $ pip install git@git.gfz-potsdam.de:fernlab/products/data-portal/s2downloader.git

If you don't have `pip`_ installed, this `Python installation guide`_ can guide
you through the process.



.. note::

    S2Downloader has been tested with Python 3.6+., i.e., should be fully compatible to all Python versions from 3.6 onwards.


.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/
.. _conda: https://conda.io/docs
