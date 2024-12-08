from setuptools import setup, find_packages

setup(
    name="ai-doctor-easy",
    version="0.1.0",
    description="AI Doctor Easy Application",
    author="MKBJ",
    author_email="chenwenlongofficial@gmail.com",
    packages=find_packages(),
    install_requires=[
        "streamlit",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    # If you have any package data files, specify them here
    package_data={
        "": ["*.txt", "*.json", "*.csv"],  # Add any data file patterns you need
    },
    # If you have any scripts or entry points
    entry_points={
        "console_scripts": [
            "ai-doctor=src.App:main",  # Adjust this according to your main function
        ],
    },
)
