from setuptools import setup, find_packages

setup(
    name='biocurator_assistant',
    version='0.1',
    packages=find_packages(),
    install_requires=[
        'pyyaml',   # add other dependencies here
        'openai'
    ],
    include_package_data=True,
    description='Biocurator Assistant',
    author='FlyBase',
    author_email='none',
    url='https://github.com/FlyBase/biocurator-assistant',
)
