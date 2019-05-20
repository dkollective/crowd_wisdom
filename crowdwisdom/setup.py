from setuptools import find_packages, setup


def load_install_requires():
    with open('requirements.txt') as f:
        lines = f.readlines()
    return lines


setup(
    name='crowdwisdom',
    version='0.0.0',
    packages=find_packages(),
    install_requires=load_install_requires(),
    extras_require={
        'example': [
            'ipdb',
            'jupyter',
            'jupyter-client',
            'jupyter-console',
            'ipython',
            'pylint',
            'flake8',
            'matplotlib',
            'seaborn'
        ]
    },
    scripts=[
        'scripts/debug',
        'scripts/backend'
    ]
)
