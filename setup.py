from setuptools import setup, find_packages

setup(
    name="cyber-owl-servo",
    version="0.1.0",
    description="Servo control module for Cyber Owl using Modbus RTU",
    packages=find_packages(where="app"),
    package_dir={"": "app"},
    install_requires=[
        "fastapi",
        "uvicorn",
        "pymodbus",
        "python-dotenv",
        "pydantic",
    ],
    entry_points={
        "console_scripts": [
            "cyber-owl-servo=app.main:main",
        ],
    },
)