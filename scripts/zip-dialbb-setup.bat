set current=%cd%
cd setup-files
del ..\docs\files\dialbb-setup.zip
copy ..\dist\dialbb*.whl .
zip -r ..\docs\files\dialbb-setup.zip dialbb*.whl README.txt install.bat uninstall.bat start-dialbb-nc.bat 
cd %current%
