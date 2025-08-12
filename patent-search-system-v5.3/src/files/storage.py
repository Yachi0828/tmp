# src/files/storage.py
'''
是否要限制檔案類型（副檔名篩選）？
上傳路徑是否要加上日期/使用者專屬子目錄以避免命名衝突、方便後續清理？
若未來需要雲端儲存（S3、MinIO），需改寫適配邏輯。
'''
import os
import shutil
from src.config import settings

class FileStorage:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_PATH
        os.makedirs(self.upload_dir, exist_ok=True)

    def save_file(self, file_obj, filename: str) -> str:
        """
        將上傳檔案儲存至伺服器
        回傳儲存後的完整路徑
        """
        file_path = os.path.join(self.upload_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file_obj.file, buffer)
        return file_path

    def delete_file(self, filename: str) -> bool:
        """
        刪除指定檔案，若成功回傳 True
        """
        file_path = os.path.join(self.upload_dir, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False