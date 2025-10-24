set current=%cd%
cd dist
del ..\docs\files\dialbb-setup.zip
zip -r ..\docs\files\dialbb-setup.zip dialbb*.whl README.txt install.bat uninstall.bat start-dialbb-nc.bat 
cd %current%
