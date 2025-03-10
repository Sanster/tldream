@echo off

set PATH=C:\Windows\System32;%PATH%

@call installer\Scripts\activate.bat

@call conda-unpack

@call conda install -y -c conda-forge cudatoolkit=11.7
@call pip install torch==1.13.1+cu117 --extra-index-url https://download.pytorch.org/whl/cu117
@call pip install xformers
@call pip3 install -U tldream

tldream --start-web-config --config-file %0\..\installer_config.json

PAUSE
