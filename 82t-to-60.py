#!/usr/bin/env python

# This tool allows you to use ComLink program with new JA-82T adapter
# ComLink needs serial port (or serial to USB converter), however JA-82T acts as a HID
# And newer Olink tool cannot communicate with JA-60 systems.
# So, to use ComLink with JA-82T and JA-60 system, you need to do this:
# 1) Install ComLink to qemu virtual machine (I didn't have time to test if it works in wine or not). But if it does, you can use socat to forward data
# 2) Connect the JA-82T to control panel and to the computer, this will create a /dev/hidrawN device (if not, modprobe hidraw)
# 3) Check permissions on /dev/hidrawN
# 4) Launch this script: ./82t-to-60.py /dev/hidrawN 4444
# 5) Launch qemu with -serial tcp:127.0.0.1:4440
# 6) Launch ComLink, connect, and work :)
# 
# This script is a quick and dirty hack, I didn't believe it would work :)

import sys
import socket
import select
from time import sleep

hid_read = True
sock_read = True
sock_ready = True


def read_hid(fp):
    data = fp.read(64)
    hid_read = True
    return data

#def incoming_hid_pkt(future_data):
#    data = future_data.result()
def incoming_hid_pkt(data):
    global sock_ready
    print("Incoming hid packet, length: "+str(len(data)))
    if len(data) is not 64:
        print("Invalid datasize for incoming hid packet: "+str(len(data)))
        return

    datasize = data[1]
    dec_data = []
    for i in range(2, datasize + 2):
        dec_data.append(data[i])
    try:
        cs.send(bytes(dec_data))
        print("sent data to socket: "+bytes(dec_data).hex())
    except Exception as e:
        sock_ready = False
        print(e)

def incoming_tcp_pkt(data):
    global sock_ready
    print("Incoming tcp packet, length: "+str(len(data)))
    if len(data) <= 0:
        sock_ready = False
        return
    hid_pkt = [ ]
    hid_pkt.append(0x00)
    hid_pkt.append(0x02)
    hid_pkt.append(len(data))
    for i in range(0, 64):
        if i < (len(data)):
            hid_pkt.append(data[i])
        else:
            hid_pkt.append(0x00)
    print("sent data to hid: "+bytes(hid_pkt).hex())
    hidfd.write(bytes(hid_pkt))


def init_82t(hidfd):
    hid_pkt = [ ]
    for i in range(0, 65):
        hid_pkt.append(0x00)
    hid_pkt[0] = 0x00

    hid_pkt[2] = 0x01
    hid_pkt[3] = 0x01
    hidfd.write(bytes(hid_pkt))
    hid_pkt[2] = 0x00
    hid_pkt[1] = 0x01
    hidfd.write(bytes(hid_pkt))


if __name__ == "__main__":
    if len(sys.argv) is not 3:
        print("Usage: "+sys.argv[0]+" JA-82T-hidraw-device tcp-port")
        sys.exit(1)

    hidfd = open(sys.argv[1], "r+b", 0)
    init_82t(hidfd)

    host = '127.0.0.1'
    port = int(sys.argv[2])
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(5)
    print("Waiting for client connect to "+host+":"+str(port))
    (cs, address) = s.accept()
    print("Connected!")

#    executor = concurrent.futures.ThreadPoolExecutor(2)
    while sock_ready is True:
#        if hid_read is True:
#            print("starting read future...")
#            future_file = executor.submit(read_hid, hidfd)
#            hid_read = False
#            future_file.add_done_callback(incoming_hid_pkt)
#            print("future started")
    
        srd, swd, sed = select.select([cs, hidfd], [], [], 10)
        for sock in srd:
            if sock is cs:
                print("reading from socket")
                data = sock.recv(64)
                incoming_tcp_pkt(data)
            if sock is hidfd:
                print("reading from hid")
                data = hidfd.read(64)
                incoming_hid_pkt(data)
    cs.close()
    s.close()
