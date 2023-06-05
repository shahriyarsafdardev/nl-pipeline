from pydantic import BaseSettings


class Settings(BaseSettings):
    pinecone_api_key: str
    pinecone_env: str
    pinecone_index_name: str
    sphere_aws_access_key_id: str
    sphere_aws_secret_access_key: str
    rds_username: str
    rds_password: str
    rds_hostname: str
    rds_port: int
    rds_db_name: str
    openai_api_key: str
    sphere_aws_s3_bucket_name: str
    scraping_bee_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()
