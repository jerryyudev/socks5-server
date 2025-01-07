import socket
import threading
import select

# 新的函数，用于判断是否是 chatgpt.com
def is_chatgpt(domain):
    return domain == 'chatgpt.com'

# 新的函数，用于通过另一个 SOCKS5 代理服务器转发请求
def forward_to_other_proxy(domain, port):
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    remote_socket.connect(('85.194.243.117', 17650))  # 连接到另一个 SOCKS5 代理

    # 发送一个新的 SOCKS5 握手请求
    remote_socket.send(b'\x05\x00')  # 没有认证
    remote_socket.recv(2)  # 接收握手响应

    # 向目标 SOCKS5 代理发送 CONNECT 请求
    remote_socket.send(b'\x05\x01\x00\x03' + bytes([len(domain)]) + domain.encode() + port.to_bytes(2, 'big'))
    response = remote_socket.recv(10)  # 接收目标代理的响应
    if response[1] != 0x00:
        print(f"Failed to connect to {domain}:{port} via other proxy.")
        remote_socket.close()
        return None

    return remote_socket

def handle_client(client_socket):
    try:
        # 第1步：接收客户端发来的 SOCKS5 握手请求
        version = client_socket.recv(1)
        if not version or version != b'\x05':  # 检查版本号是否为 0x05
            print(f"Invalid SOCKS version: {version}")
            return

        nmethods = client_socket.recv(1)
        if not nmethods:
            print(f"No method count received")
            return
        nmethods = ord(nmethods)  # 将字节转换为整数

        methods = client_socket.recv(nmethods)
        if len(methods) != nmethods:
            print(f"Incomplete methods received: {methods}")
            return

        # 第2步：响应 SOCKS5 握手协议，选择不需要认证
        client_socket.send(b'\x05\x00')  # 表示选择不需要认证

        # 第3步：接收客户端的请求
        header = client_socket.recv(4)
        if len(header) != 4:
            print(f"Incomplete header received: {header}")
            return

        version, cmd, rsv, atyp = header

        if cmd == 1:  # 如果是 CONNECT 请求
            if atyp == 1:  # IPv4 地址
                addr = socket.inet_ntoa(client_socket.recv(4))
                port = int.from_bytes(client_socket.recv(2), 'big')
                print(f"Connecting to {addr}:{port}")
            elif atyp == 3:  # 域名
                domain_len = client_socket.recv(1)
                if not domain_len:
                    print(f"No domain length received")
                    return
                domain_len = ord(domain_len)
                domain = client_socket.recv(domain_len).decode()
                port = int.from_bytes(client_socket.recv(2), 'big')
                print(f"Connecting to domain: {domain}:{port}")
                addr = domain
            else:
                print(f"Unsupported address type: {atyp}")
                return

            # 第4步：根据目标地址选择代理方式
            if is_chatgpt(domain):
                print(f"Requesting {domain} via another proxy...")
                remote_socket = forward_to_other_proxy(domain, port)
                if not remote_socket:
                    client_socket.send(b'\x05\x01\x00\x01' + socket.inet_aton('0.0.0.0') + b'\x00\x00')  # 连接失败
                    client_socket.close()
                    return
            else:
                # 如果是普通网站，直接连接目标
                try:
                    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    remote_socket.connect((addr, port))
                except Exception as e:
                    print(f"Error connecting to {addr}:{port}: {e}")
                    client_socket.send(b'\x05\x01\x00\x01' + socket.inet_aton('0.0.0.0') + b'\x00\x00')  # 连接失败
                    client_socket.close()
                    return

            # 第5步：成功连接，回复客户端
            client_socket.send(b'\x05\x00\x00\x01' + socket.inet_aton('0.0.0.0') + b'\x00\x00')

            # 第6步：开始转发数据
            while True:
                r, w, x = select.select([client_socket, remote_socket], [], [])
                if client_socket in r:
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    remote_socket.sendall(data)  # 使用 sendall 确保数据完整发送
                if remote_socket in r:
                    data = remote_socket.recv(4096)
                    if not data:
                        break
                    client_socket.sendall(data)
            print("Data transfer completed.")
        client_socket.close()
    except Exception as e:
        print(f"Error handling client: {e}")
        client_socket.close()

def start_proxy_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 添加端口复用
    server.bind(('0.0.0.0', 17650))
    server.listen(5)
    print("SOCKS5 Proxy Server started on port 17650")

    while True:
        client_socket, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.daemon = True  # 设置线程为守护线程，主线程退出时子线程也退出
        client_handler.start()

if __name__ == "__main__":
    start_proxy_server()
