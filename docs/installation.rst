.. _installation:

============
Installation
============


Using Conda or Mamba (recommended)
-----------------------------------------

Create a conda environment:

```
conda create --name myenv python --no-default-packages
conda activate myenv
```

Installing `s2downloader` from the `conda-forge` channel can be achieved by adding `conda-forge` to your channels with:

```
conda config --add channels conda-forge
conda config --set channel_priority strict
```

Once the `conda-forge` channel has been enabled, `s2downloader` can be installed with `conda`:

```
conda install s2downloader
```

or with `mamba`:

```
mamba install s2downloader
```


Using pip
---------------------------
```
pip install s2downloader
```


.. note::

    S2Downloader has been tested with Python 3.10+., i.e., should be fully compatible to all Python versions from 3.10 onwards.


.. _pip: https://pip.pypa.io
.. _Python installation guide: http://docs.python-guide.org/en/latest/starting/installation/
.. _conda: https://conda.io/docs
