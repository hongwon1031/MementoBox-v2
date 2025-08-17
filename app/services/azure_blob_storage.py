import os
from azure.storage.blob import BlobServiceClient, BlobClient
from datetime import datetime
from typing import Optional, Literal
from core.config import settings

ContainerType = Literal["photo", "talking-voice"]

class BlobStorageService:
    def __init__(self, container_type: ContainerType = "photo"):
        # 환경 변수에서 설정 가져오기
        self.account_name = os.getenv("AZURE_BLOBSTORAGE_ACCOUNT")
        self.account_key = os.getenv("AZURE_BLOBSTORAGE_KEY")
        
        # 컨테이너 타입에 따라 다른 컨테이너 이름 사용
        self.container_name = container_type
        
        # 연결 문자열 생성
        connection_string = f"DefaultEndpointsProtocol=https;AccountName={self.account_name};AccountKey={self.account_key};EndpointSuffix=core.windows.net"
        
        # Blob Service Client 생성
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(self.container_name)

    async def upload_file(self, file_data: bytes, filename: str) -> tuple[str, str]:
        """
        파일을 Azure Blob Storage에 업로드하고 URL과 blob_name을 반환합니다.
        """
        # 타임스탬프를 포함한 고유한 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        blob_name = f"{timestamp}_{filename}"
        
        # Blob 클라이언트 생성
        blob_client = self.container_client.get_blob_client(blob_name)
        
        # 파일 업로드
        blob_client.upload_blob(file_data, overwrite=True)
        
        # Blob URL 생성
        blob_url = blob_client.url
        
        return blob_url, blob_name

    async def download_file(self, blob_url: str) -> bytes:
        """
        Azure Blob Storage에서 파일을 다운로드하여 bytes로 반환합니다.
        """
        try:
            # URL 파싱: https://{account}.blob.core.windows.net/{container}/{blob_name}
            url_parts = blob_url.split('/')
            if len(url_parts) < 5:
                raise ValueError(f"Invalid blob URL format: {blob_url}")
            
            # 컨테이너와 blob_name 추출
            container_name = url_parts[4]  # https://account.blob.core.windows.net/container/...
            blob_name = '/'.join(url_parts[5:])  # blob_name (경로가 포함될 수 있음)
            
            print(f"🔍 URL 파싱 결과:")
            print(f"   - Container: {container_name}")
            print(f"   - Blob name: {blob_name}")
            print(f"   - Current container: {self.container_name}")
            
            # 컨테이너 불일치 체크
            if container_name != self.container_name:
                print(f"⚠️ 컨테이너 불일치: URL={container_name}, Service={self.container_name}")
                # URL에서 추출한 컨테이너로 새로운 클라이언트 생성
                correct_container_client = self.blob_service_client.get_container_client(container_name)
                blob_client = correct_container_client.get_blob_client(blob_name)
            else:
                blob_client = self.container_client.get_blob_client(blob_name)
            
            # 파일 다운로드
            download_stream = blob_client.download_blob()
            return download_stream.readall()
        except Exception as e:
            print(f"Error downloading blob: {str(e)}")
            print(f"Full URL: {blob_url}")
            raise e

    async def delete_file(self, blob_name: str) -> bool:
        """
        Azure Blob Storage에서 파일을 삭제합니다.
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_name)
            blob_client.delete_blob()
            return True
        except Exception as e:
            print(f"Error deleting blob: {str(e)}")
            return False

async def download_file_from_url(blob_url: str) -> bytes:
    """
    URL을 직접 사용하여 Azure Blob Storage에서 파일을 다운로드합니다.
    컨테이너 타입에 상관없이 URL만으로 다운로드가 가능합니다.
    """
    try:
        # 환경 변수에서 설정 가져오기
        account_name = os.getenv("AZURE_BLOBSTORAGE_ACCOUNT")
        account_key = os.getenv("AZURE_BLOBSTORAGE_KEY")
        
        # 연결 문자열 생성
        connection_string = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={account_key};EndpointSuffix=core.windows.net"
        
        # BlobClient를 URL에서 직접 생성 (올바른 방법)
        blob_client = BlobClient.from_blob_url(blob_url, credential=account_key)
        
        print(f"🔍 Blob 정보:")
        print(f"   - Account: {blob_client.account_name}")
        print(f"   - Container: {blob_client.container_name}")
        print(f"   - Blob: {blob_client.blob_name}")
        
        # 파일 다운로드
        download_stream = blob_client.download_blob()
        return download_stream.readall()
        
    except Exception as e:
        print(f"Error downloading blob from URL: {str(e)}")
        print(f"URL: {blob_url}")
        raise e

def get_blob_service_client(container_type: ContainerType = "photo") -> BlobStorageService:
    """
    BlobStorageService의 인스턴스를 생성하여 반환합니다.
    """
    return BlobStorageService(container_type) 