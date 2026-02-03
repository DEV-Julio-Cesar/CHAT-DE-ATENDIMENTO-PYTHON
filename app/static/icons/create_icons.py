#!/usr/bin/env python3
"""Script para criar ícones PNG simples para o PWA"""

import base64
import struct
import zlib
from pathlib import Path

def create_simple_png(width: int, height: int, color: tuple = (0, 100, 180)) -> bytes:
    """Cria um PNG simples com cor sólida"""
    
    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        return struct.pack('>I', len(data)) + chunk + struct.pack('>I', zlib.crc32(chunk) & 0xffffffff)
    
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk (header)
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    ihdr = png_chunk(b'IHDR', ihdr_data)
    
    # IDAT chunk (image data)
    raw_data = b''
    for y in range(height):
        raw_data += b'\x00'  # Filter byte (none)
        for x in range(width):
            raw_data += bytes(color)  # RGB
    
    compressed_data = zlib.compress(raw_data, 9)
    idat = png_chunk(b'IDAT', compressed_data)
    
    # IEND chunk (end)
    iend = png_chunk(b'IEND', b'')
    
    return signature + ihdr + idat + iend


def main():
    icons_path = Path(__file__).parent
    
    # Cor CIANET azul
    cianet_blue = (0, 100, 200)
    
    # Criar ícones em diferentes tamanhos
    sizes = [192, 512]
    
    for size in sizes:
        icon_data = create_simple_png(size, size, cianet_blue)
        icon_path = icons_path / f"icon-{size}x{size}.png"
        
        with open(icon_path, 'wb') as f:
            f.write(icon_data)
        
        print(f"Criado: {icon_path} ({len(icon_data)} bytes)")
    
    # Criar ícones maskable
    for size in sizes:
        icon_data = create_simple_png(size, size, cianet_blue)
        icon_path = icons_path / f"maskable-{size}x{size}.png"
        
        with open(icon_path, 'wb') as f:
            f.write(icon_data)
        
        print(f"Criado: {icon_path} ({len(icon_data)} bytes)")
    
    print("\nTodos os ícones foram criados!")


if __name__ == "__main__":
    main()
