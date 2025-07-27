import os, requests
from notion_client import Client
from dotenv import load_dotenv
from urllib.parse import urlparse, parse_qs
import mimetypes

load_dotenv()
token = os.getenv("notion_key")
database_id = 'xxx'
client = Client(auth=token)

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28"
}

def create_upload_object():
    resp = requests.post(
        "https://api.notion.com/v1/file_uploads",
        headers={
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        },
        json={}  # 一定要是空 JSON
    )
    resp.raise_for_status()
    return resp.json()


def send_upload_content(upload_id, path):
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as f:
        r = requests.post(
            f"https://api.notion.com/v1/file_uploads/{upload_id}/send",
            headers=HEADERS,
            files={"file": (os.path.basename(path), f, mime)}
        )
    r.raise_for_status()
    return r.json()

def upload_image_file(path):
    obj = create_upload_object()  # 👈 no args
    upload_id = obj["id"]
    send_upload_content(upload_id, path)
    return upload_id

def download_image_from_url(url: str, save_dir: str = "./downloads") -> str:
    """
    下载远程图片并保存到本地，自动补全扩展名（如 png、jpg）
    :param url: 图片 URL
    :param save_dir: 保存目录
    :return: 本地文件路径
    """
    try:
        os.makedirs(save_dir, exist_ok=True)

        # 获取基本文件名
        path_part = urlparse(url).path  # /media/xxx
        filename_base = os.path.basename(path_part)  # Gws96xmbgAU-PQD

        # 获取扩展名（从 query 解析）TW 
        query = parse_qs(urlparse(url).query)
        ext = query.get("format", ["jpg"])[0]  # 默认 jpg
        filename = f"{filename_base}.{ext}"

        filepath = os.path.join(save_dir, filename)

        # 下载图片
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        with open(filepath, "wb") as f:
            f.write(response.content)

        print(f"✅ 图片保存成功: {filepath}")
        return filepath

    except Exception as e:
        print(f"❌ 图片下载失败: {url}\n错误: {e}")
        raise
# 使用示例
localImage = download_image_from_url("https://pbs.twimg.com/media/Gws96xmbgAU-PQD?format=png&name=orig")
file_upload_id = upload_image_file(localImage)

resp = client.pages.create(
    parent={"database_id": database_id},
    properties={
        "标题": {"title":[{"text":{"content":"本地图片上传测试"}}]}
    },
    children=[{
        "object":"block",
        "type":"image",
        "image":{
            "type":"file_upload",
            "file_upload":{"id":file_upload_id}
        }
    }]
)
print("✅ 页面 URL:", resp.get("url"))
