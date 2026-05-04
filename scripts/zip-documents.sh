#!/bin/bash

rm docs/files/document-ja.zip
rm docs/files/document-en.zip

pushd docs/document-ja/build
zip -r ../../../docs/files/document-ja.zip html
popd

pushd docs/document-en/build
zip -r ../../../docs/files/document-en.zip html
popd


