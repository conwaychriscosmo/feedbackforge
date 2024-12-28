from setuptools import setup, find_packages

setup(
    name="feedback_forge_python_sdk",
    version="1.0.0",
    author="Claude & ChatGPT",
    author_email="info@feedbackforge.xyz",
    description="A Python SDK for processing documents with Feedback Forge.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/conwaychriscosmo/feedbackforge",
    packages=find_packages(),
    install_requires=[
        "pyyaml",
        "requests",
        "python-crontab"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)