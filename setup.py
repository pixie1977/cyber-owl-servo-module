from setuptools import setup, find_packages

setup(
    name="cyber-owl-tts",
    version="0.1.0",
    description="TTS module for Russian voice synthesis using Silero",
    packages=find_packages(where="app"),
    package_dir={"": "app"},
    install_requires=[
        "torch",
        "torchaudio",
        "omegaconf",
        "pygame",
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "cyber-owl-tts=cyber_owl_tts.core.text_to_speech:main",
        ],
    },
)