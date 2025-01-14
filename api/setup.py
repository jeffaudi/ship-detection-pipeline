"""Setup module for the application."""

from setuptools import find_packages, setup

setup(
    name="ship-detection-api",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask==2.0.3",
        "Werkzeug==2.0.3",
        "Flask-Cors==3.0.10",
        "supabase==2.11.0",
        "sentinelsat==1.2.1",
    ],
)
