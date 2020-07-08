import os
import subprocess
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	reqs = f.read()
reqs = reqs.strip().splitlines()

SRCDIR = os.path.dirname(os.path.abspath(__file__))
VERSION = subprocess.check_output(
    f"cd {SRCDIR} && git rev-parse --short HEAD", shell=True
).decode('ascii').strip()

setup(
	name='discord-monopoly',
	version='0.0a' + VERSION,
	description='Play Monopoly on Discord',
	url='https://github.com/Kenny2github/discord-monopoly',
	author='Kenny2github',
	author_email='kenny2minecraft@gmail.com',
	classifiers=[
		'Development Status :: 3 - Alpha',
		'Topic :: Communications :: Chat',
		'Topic :: Games/Entertainment :: Turn Based Strategy',
		'License :: OSI Approved :: MIT License',
		'Operating System :: Microsoft :: Windows :: Windows 10',
		'Operating System :: POSIX :: Linux',
		'Programming Language :: Python :: 3 :: Only',
		'Programming Language :: Python :: 3.7',
	],
	keywords='discord bot monopoly',
	packages=find_packages(),
	install_requires=reqs,
	python_requires='>=3.7',
)
