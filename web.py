import os
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

# 使用 os.path.exists() 进行检查
folder_path = r'F:\file'
if os.path.exists(folder_path) and os.path.isdir(folder_path):
    os.chdir(folder_path)
else:
    print(f"路径不存在或不是目录: {folder_path}")
    exit(1)

# 启动 HTTP 服务器
PORT = 8000

with TCPServer(("", PORT), SimpleHTTPRequestHandler) as httpd:
    print(f"Serving files from {folder_path} on port {PORT}")
    httpd.serve_forever()
