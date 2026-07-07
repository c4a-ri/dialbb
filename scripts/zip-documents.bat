del docs\files\document-ja.zip
del docs\files\document-en.zip

cd docs\document-ja\build
zip -r ..\..\..\docs\files\document-ja.zip html
cd ..\..\..\

cd docs\document-en\build
zip -r ..\..\..\docs\files\document-en.zip html
cd ..\..\..\


