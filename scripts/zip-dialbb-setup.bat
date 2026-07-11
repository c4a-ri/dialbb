set current=%cd%
cd setup-files
del ..\docs\files\dialbb-setup.zip
zip -r ..\docs\files\dialbb-setup.zip README.txt install.bat uninstall.bat start-dialbb-nc.bat start-dialbb-nc-en.bat 
cd %current%
