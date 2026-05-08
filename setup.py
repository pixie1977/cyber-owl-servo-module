"""
Setup configuration for Cyber Owl Servo — модуль управления сервоприводами
через Modbus RTU.
"""

from setuptools import find_packages, setup


# Чтение README.md
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="cyber-owl-servo",
    version="0.1.0",
    description="Servo control module for Cyber Owl using Modbus RTU over RS485",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Pixie",
    author_email="eugenmac56@gmail.com",
    url="https://github.com/pixie1977/cyber-owl-servo-module",
    license="MIT",
    packages=find_packages(where="app"),
    package_dir={"": "app"},
    include_package_data=True,
    python_requires=">=3.9",
    install_requires=[
        "fastapi==0.129.0",
        "fuzzywuzzy==0.18.0",
        "omegaconf==2.3.0",
        "pydantic==2.12.5",
        "pygame==2.6.1",
        "python-dotenv==1.2.1",
        "setuptools==80.3.1",
        "sounddevice==0.5.2",
        "torch==2.7.1",
        "uvicorn==0.40.0",
        "numpy==1.23.5",
        "python-Levenshtein",
        "python-multipart",
        "scipy",
        "pymodbus==3.8.0",
    ],
    entry_points={
        "console_scripts": [
            "cyber-owl-servo=app.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Hardware :: Hardware Drivers",
    ],
    keywords="modbus rtu servo robotics cyber-owl",
)