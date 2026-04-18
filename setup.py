"""
Rokan Skill Pack for OpenClaw
The Player. Linux-first. No cloud leaks.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="rokan-skills",
    version="1.0.0",
    author="ixchio",
    author_email="amankumarpandeyin@gmail.com",
    description="Sung Jin-Woo edition AI assistant skills for OpenClaw",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ixchio/rokan-skills",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    install_requires=[
        "qdrant-client>=1.12.0",
        "ollama>=0.4.0",
        "pydantic>=2.9.0",
        "pyyaml>=6.0.1",
        "psutil>=6.0.0",
        "requests>=2.32.0",
        "textual>=0.50.0",
        "openai>=1.12.0",
        "edge-tts>=6.1.12",
    ],
    extras_require={
        "memory": ["mem0ai>=0.1.0"],
        "research": [
            "tavily-python>=0.5.0",
            "crawl4ai>=0.4.0",
            "praw>=7.7.0",
            "tweepy>=4.14.0",
        ],
        "voice": [
            "openwakeword>=0.6.0",
            "pyaudio>=0.2.14",
            "webrtcvad>=2.0.10",
        ],
        "jobs": ["apscheduler>=3.10.0", "discord-webhook>=1.2.0"],
        "code": ["restrictedpython>=7.0"],
        "vcr": ["ai-agent-vcr>=0.1.0"],
        "all": [
            "mem0ai>=0.1.0",
            "tavily-python>=0.5.0",
            "crawl4ai>=0.4.0",
            "praw>=7.7.0",
            "tweepy>=4.14.0",
            "openwakeword>=0.6.0",
            "pyaudio>=0.2.14",
            "apscheduler>=3.10.0",
            "restrictedpython>=7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "rokan=rokan_cli.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
