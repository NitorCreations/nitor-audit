#!/bin/bash
rm -rf build dist
VERSION=$1
MESSAGE="$2"
bumpversion --new-version $VERSION --message "$MESSAGE" setup.py
python setup.py sdist bdist_wheel
gpg -o dist/nitor_audit-${VERSION}-py2.py3-none-any.whl.asc -a -b dist/nitor_audit-${VERSION}-py2.py3-none-any.whl
gpg -o dist/nitor-audit-${VERSION}.tar.gz.asc -a -b dist/nitor-audit-${VERSION}.tar.gz
twine upload dist/*
