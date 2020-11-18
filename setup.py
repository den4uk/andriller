import os.path
from setuptools import setup
from andriller import __version__, __website__, __package_name__

req = os.path.join(os.path.dirname(__file__), 'requirements.txt')
with open(req, 'rt', encoding="utf-8") as f:
    install_requires = [dep for dep in f.read().splitlines() if not dep.startswith('#')]

reme = os.path.join(os.path.dirname(__file__), 'README.md')
with open(reme, 'rt', encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='andriller',
    scripts=['andriller-gui.py'],
    version=__version__,
    description='Andriller CE | Android Forensic Tools',
    author='Denis Sazonov',
    author_email='den@saz.lt',
    url=__website__,
    packages=[__package_name__],
    license='MIT License',
    keywords="andriller android forensic forensics adb dfir".split(),
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=install_requires,
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    zip_safe=True)
