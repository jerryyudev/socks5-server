import socket
import threading

def handle_client(client_socket):
    try:
        # 第1步：接收客户端发来的 SOCKS5 握手请求
        version = client_socket.recv(1)
        if not version or version != b'\x05': # 检查版本号是否为 0x05
            print(f"Invalid SOCKS version: {version}")
            return

        nmethods = client_socket.recv(1)
        if not nmethods:
            print(f"No method count received")
            return
        nmethods = ord(nmethods) # 将字节转换为整数

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

            # 第4步：连接目标地址
            try:
                remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote_socket.connect((addr, port))

                # 第5步：成功连接，回复客户端
                client_socket.send(b'\x05\x00\x00\x01' + socket.inet_aton('0.0.0.0') + b'\x00\x00')

                # 第6步：开始转发数据
                while True:
                    r, w, x = select.select([client_socket, remote_socket], [], [])
                    if client_socket in r:
                        data = client_socket.recv(4096)
                        if not data:
                            break
                        remote_socket.sendall(data) # 使用 sendall 确保数据完整发送
                    if remote_socket in r:
                        data = remote_socket.recv(4096)
                        if not data:
                            break
                        client_socket.sendall(data)
                print("Data transfer completed.")
            except Exception as e:
                print(f"Error connecting to remote: {e}")
                client_socket.send(b'\x05\x01\x00\x01' + socket.inet_aton('0.0.0.0') + b'\x00\x00') #Connection refused
                if remote_socket:
                    remote_socket.close()

        client_socket.close()
    except Exception as e:
        print(f"Error handling client: {e}")
        client_socket.close()

import select #导入select模块
def start_proxy_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #添加端口复用
    server.bind(('0.0.0.0', 17650)) #这里可以修改端口号
    server.listen(5)
    print("SOCKS5 Proxy Server started on port 17650") #测试：curl --socks5 85.194.243.117:17650 ip-api.com

    while True:
        client_socket, addr = server.accept()
        print(f"Accepted connection from {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.daemon = True #设置线程为守护线程，主线程退出时子线程也退出
        client_handler.start()

if __name__ == "__main__":
    start_proxy_server()
