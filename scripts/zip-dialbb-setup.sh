pushd setup-files
rm ../docs/files/dialbb-setup.zip 
zip -r ../docs/files/dialbb-setup.zip README.txt install.bat uninstall.bat start-dialbb-nc.bat start-dialbb-en.bat 
popd
