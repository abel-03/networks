import socket
import logging
import time

class UDPBasedProtocol:
    def __init__(self, *, local_addr, remote_addr):
        self.udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.udp_socket.settimeout(0.0001)
        self.remote_addr = remote_addr
        self.udp_socket.bind(local_addr)

    def sendto(self, data):
        return self.udp_socket.sendto(data, self.remote_addr)

    def recvfrom(self, n):
        msg, addr = self.udp_socket.recvfrom(n)
        return msg
        
    def close(self):
        self.udp_socket.close()
        
def sleep():
    time.sleep(0.001)

max_count = 5
count_start = 0

class MyTCPProtocol(UDPBasedProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_connected = False
        self.buffer_size = 1024
        self.block_size = self.buffer_size - 6
        self.packets = []
        self.acknowledgment = 0

    def sendConnect(self):
        while True:
            self.sendto(int.to_bytes(count_start, 1, 'big'))
            try:
                flag = self.recvfrom(self.buffer_size)
                flag = int.from_bytes(flag, 'big')
                if flag == count_start:
                    break
            except Exception as e:
                sleep()
                pass
        self.is_connected = True

    def send(self, data: bytes):
        if not self.is_connected:
            self.sendConnect()
        self.packets = []
        for i in range(0, len(data), self.block_size):            
            word = data[i : i + self.block_size]
            self.packets.append([len(word), word])

        for packet_id in range(len(self.packets)):
            block = int.to_bytes(len(self.packets), 2, 'big') + \
               int.to_bytes(self.acknowledgment, 4, 'big') + \
               self.packets[packet_id][1]
            for packet_count in range(1, max_count):
                for k in range(max_count):
                    self.sendto(block)
                flag = 0
                while True:
                    try:
                        ack = int.from_bytes(self.recvfrom(self.buffer_size)[2:6], 'big')
                        if ack > self.acknowledgment:
                            self.acknowledgment = ack
                            flag = 1
                            break
                    except Exception as e:
                        sleep()
                        break
                if flag:
                    break
        return len(data)
    
    def recvConnect(self):
        while True:
            try:
                data = self.recvfrom(self.buffer_size)
                data = int.from_bytes(data, 'big')
                if data == count_start:
                    self.sendto(int.to_bytes(count_start, 2, 'big'))
                    break
            except Exception as e:
                sleep()
                pass
        self.is_connected = True

    def parsePacket(self, data: bytes):
        response = {}
        flag = int.from_bytes(data[:2], 'big')
        if flag == count_start:
            return {}
        response['count'] = flag
        response['acknowledgment'] = int.from_bytes(data[2:6], 'big')
        response['data'] = data[6:]

        return response

    def recv(self, n: int):
        if not self.is_connected:
            self.recvConnect()
            
        answer = bytes()
        flag = 0
        packet_count = 0
        while not flag:
            cnt_received_packets = 0
            while True and cnt_received_packets < max_count:
                try:
                    data = self.recvfrom(self.buffer_size)
                    if len(data) == 6:
                        continue
                    ans = self.parsePacket(data)
                    if ans == {}:
                        continue
                    ack = ans['acknowledgment']
                    if self.acknowledgment > ack:
                        continue
                    if ack == self.acknowledgment:
                        answer = answer + ans['data']
                        self.acknowledgment += len(ans['data'])
                        packet_count += 1
                        if packet_count == ans['count']:
                            flag = 1
                        break
                except Exception as e:
                    cnt_received_packets += 1
                    sleep()
                    break
            self.sendto(int.to_bytes(packet_count, 2, 'big') + int.to_bytes(self.acknowledgment, 4, 'big'))

        return answer[:n]
        
    def close(self):
        super().close()
