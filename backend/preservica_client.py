import os
from dotenv import load_dotenv
import pyPreservica as pyp

class PreservicaClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PreservicaClient, cls).__new__(cls)

            # Load from .env file
            load_dotenv()

            username = os.getenv("PRESERVICA_USERNAME")
            password = os.getenv("PRESERVICA_PASSWORD")
            tenant = os.getenv("PRESERVICA_TENANT")
            server = os.getenv("PRESERVICA_SERVER")

            try:
                cls._instance.client = pyp.EntityAPI(
                    username=username,
                    password=password,
                    tenant=tenant,
                    server=server
                )
            except Exception as e:
                import logging
                logging.error("Failed to connect to Preservica", exc_info=True)
                raise e

        return cls._instance
