"""Read a pixel from Android screencap's non-interlaced RGB/RGBA PNG, without external dependencies."""
import struct, zlib

def pixel(data, x, y):
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Not PNG')
    pos=8;compressed=bytearray();header=None
    while pos<len(data):
        size=struct.unpack('>I',data[pos:pos+4])[0];kind=data[pos+4:pos+8];chunk=data[pos+8:pos+8+size]
        if kind==b'IHDR':header=struct.unpack('>IIBBBBB',chunk)
        if kind==b'IDAT':compressed.extend(chunk)
        pos+=size+12
    width,height,depth,kind,compression,filter_,interlace=header
    if depth!=8 or kind not in (2,6) or interlace!=0 or compression!=0 or filter_!=0:raise ValueError('Unsupported screencap format')
    if not (0<=x<width and 0<=y<height):raise ValueError('Pixel outside PNG')
    channels=3 if kind==2 else 4;stride=width*channels;raw=zlib.decompress(compressed);previous=bytearray(stride)
    for row_index in range(y+1):
        offset=row_index*(stride+1);mode=raw[offset];row=bytearray(raw[offset+1:offset+1+stride])
        for i in range(stride):
            a=row[i-channels] if i>=channels else 0;b=previous[i];c=previous[i-channels] if i>=channels else 0
            if mode==1:row[i]=(row[i]+a)&255
            elif mode==2:row[i]=(row[i]+b)&255
            elif mode==3:row[i]=(row[i]+(a+b)//2)&255
            elif mode==4:
                p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
                row[i]=(row[i]+(a if pa<=pb and pa<=pc else b if pb<=pc else c))&255
            elif mode!=0:raise ValueError('Bad PNG filter')
        previous=row
    return tuple(previous[x*channels:x*channels+3])
