"""
OSINT Investigator - Setup Script
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

setup(
    name='osint-investigator',
    version='1.0.0',
    author='Security Research Team',
    description='Comprehensive Open Source Intelligence Toolkit',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/your-repo/osint-investigator',
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Security',
        'Topic :: Internet',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    python_requires='>=3.8',
    install_requires=[
        'requests>=2.31.0',
        'aiohttp>=3.9.0',
        'colorama>=0.4.6',
        'rich>=13.7.0',
        'python-dotenv>=1.0.0',
        'phonenumbers>=8.13.0',
        'email-validator>=2.1.0',
        'beautifulsoup4>=4.12.0',
        'lxml>=4.9.0',
        'pydantic>=2.5.0',
        'click>=8.1.7',
        'tqdm>=4.66.0',
        'jinja2>=3.1.2',
        'pyyaml>=6.0.1',
    ],
    entry_points={
        'console_scripts': [
            'osint-investigator=osint_tool.cli:cli',
            'osint=osint_tool.cli:cli',
        ],
    },
    include_package_data=True,
    keywords='osint security investigation reconnaissance intelligence',
)
