"""
Rokan — Ambient Intelligence for your machine.
Cross-platform (Linux + Windows). F.R.I.D.A.Y.-class desktop assistant.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="rokan",
    version="3.0.0",
    author="ixchio",
    author_email="amankumarpandeyin@gmail.com",
    description="F.R.I.D.A.Y.-class ambient intelligence — desktop assistant with memory, skills, and proactive awareness",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ixchio/rokan",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    install_requires=[
        # Core
        "pydantic>=2.9.0",
        "pyyaml>=6.0.1",
        "psutil>=6.0.0",
        "openai>=1.12.0",
        "click>=8.1.0",
        # GUI desktop app
        "flask>=3.0.0",
        # TUI (terminal fallback)
        "textual>=0.85.0",
        # Voice
        "edge-tts>=6.1.12",
        # Search (web search, no API key needed)
        "duckduckgo-search>=6.0.0",
    ],
    extras_require={
        "voice": [
            "sounddevice>=0.4.6",
            "numpy>=1.24.0",
            "faster-whisper>=1.0.0",
            "openwakeword>=0.6.0",
            "webrtcvad>=2.0.10",
        ],
        "window": ["pywebview>=5.0"],
        "search": ["duckduckgo-search>=6.0.0"],
        "research": [
            "tavily-python>=0.5.0",
            "praw>=7.7.0",
            "tweepy>=4.14.0",
        ],
        "memory-vector": [
            "qdrant-client>=1.12.0",
            "ollama>=0.4.0",
        ],
        "all": [
            "duckduckgo-search>=6.0.0",
            "sounddevice>=0.4.6",
            "numpy>=1.24.0",
            "faster-whisper>=1.0.0",
            "openwakeword>=0.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "rokan=rokan_cli.main:main",
        ],
    },
    package_data={
        "rokan_gui": ["static/*"],
    },
    include_package_data=True,
    zip_safe=False,
)
