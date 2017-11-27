#!/usr/bin/python
#
# python-v4l2captureext
#
# 2009, 2010, 2011 Fredrik Portstrom
#
# I, the copyright holder of this file, hereby release it into the
# public domain. This applies worldwide. In case this is not legally
# possible: I grant anyone the right to use this work for any
# purpose, without any conditions, unless such conditions are
# required by law.

from distutils.core import Extension, setup
setup(
    name = "v4l2captureext",
    version = "1.7",
    author = "Fredrik Portstrom",
    author_email = "fredrik@jemla.se",
    url = "http://fredrik.jemla.eu/v4l2capture",
    description = "Capture video with video4linux2",
    long_description = "python-v4l2captureext is a slim and easy to use Python "
    "extension for capturing video with video4linux2.",
    license = "Public Domain",
    classifiers = [
        "License :: Public Domain",
        "Programming Language :: C"],
    ext_modules = [
        Extension("v4l2captureext", ["v4l2captureext.c"],
        libraries=["v4l2"], extra_compile_args=['-DUSE_LIBV4L', ],
        )])
