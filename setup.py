from setuptools import setup, find_packages

setup(
    name="mailscout",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "google-api-python-client>=2.0.0",
        "google-auth-httplib2>=0.1.0",
        "google-auth-oauthlib>=1.0.0",
        "fastapi>=0.100.0",
        "uvicorn>=0.20.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "beautifulsoup4>=4.10.0",
        "httpx>=0.24.0",
    ],
    python_requires=">=3.8",
)