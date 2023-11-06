# Switch which image to use depending on target architecture
FROM rayproject/ray:2.6.3-py310-cpu         AS amd64
ENV ARCH=amd64
FROM rayproject/ray:2.6.3-py310-cpu-aarch64 AS arm64
ENV ARCH=arm64
FROM ${TARGETARCH} AS build

USER root
RUN apt-get update &&\
    apt-get install --no-install-recommends -y \
      gfortran \
      make \
      unzip

USER ray
WORKDIR /home/ray

# Copy and install ISOFIT
COPY --chown=ray:users . isofit/
RUN conda config --prepend channels conda-forge &&\
    conda update --all --yes &&\
    conda create --name isofit --clone base &&\
    conda install --name base --solver=classic conda-libmamba-solver nb_conda_kernels jupyterlab &&\
    conda env update --name isofit --solver=libmamba --file isofit/recipe/docker-loose-$ARCH.yml &&\
    conda install --name isofit --solver=libmamba ipykernel &&\
    anaconda3/envs/isofit/bin/pip install --no-deps -e isofit &&\
    echo "conda activate isofit" >> ~/.bashrc &&\
    echo "alias mi=conda install --solver=libmamba"

# Install 6S
RUN mkdir 6sv-2.1 &&\
    mv isofit/6sv-2.1.tar 6sv-2.1/ &&\
    cd 6sv-2.1 &&\
    tar -xf 6sv-2.1.tar &&\
    rm 6sv-2.1.tar &&\
    sed -i Makefile -e 's/FFLAGS.*/& -std=legacy/' &&\
    make
ENV SIXS_DIR="/home/ray/6sv-2.1"

# Install sRTMnet
RUN mkdir sRTMnet_v100 &&\
    mv isofit/sRTMnet_v100.zip sRTMnet_v100/ &&\
    cd sRTMnet_v100 &&\
    unzip sRTMnet_v100.zip &&\
    rm sRTMnet_v100.zip
ENV EMULATOR_PATH="/home/ray/sRTMnet_v100/sRTMnet_v100"

# Some ISOFIT examples require this env var to be present but does not need to be installed
ENV MODTRAN_DIR=""

# Explicitly set the shell to bash so the Jupyter server defaults to it
ENV SHELL=/bin/bash

# Ray Dashboard port
EXPOSE 8265

# Start the Jupyterlab server
EXPOSE 8888
CMD isofit/startJupyterDocker.sh
