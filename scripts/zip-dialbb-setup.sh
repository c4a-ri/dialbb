pushd setup-files
rm ../docs/files/dialbb-setup.zip 
cp ../dist/dialbb*.whl .
zip -r ../docs/files/dialbb-setup.zip dialbb*.whl README.txt install.bat uninstall.bat start-dialbb-nc.bat 
popd
