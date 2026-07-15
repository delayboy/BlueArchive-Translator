from setuptools import setup, Extension

fastcrc_module = Extension(
    'crcmanip.fastcrc',
    sources=['fastcrc.c'],
)

setup(
    name='crcmanip_fastcrc',
    version='1.0',
    description='Fast CRC C extension for Python',
    ext_modules=[fastcrc_module],
)
