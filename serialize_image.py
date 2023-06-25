# import necessary libraries
import binascii

# specify file paths
input_image_path = 'img.jpg'
output_c_path = 'output.c'

# read the image file
with open(input_image_path, 'rb') as image_file:
    # read the image as bytes
    byte_content = image_file.read()

# count the number of bytes
num_bytes = len(byte_content)

# open the output file
with open(output_c_path, 'w') as output_file:
    # write the array to the file
    output_file.write('#include "output.h"\n\n')

    # begin array
    output_file.write('const uint8_t img[] = {\n')

    # format bytes and add newline after every chunk
    chunk_size = 12
    for i in range(0, num_bytes, chunk_size):
        chunk = byte_content[i: i + chunk_size]
        formatted_chunk = ", ".join("0x{:02X}".format(b) for b in chunk)
        output_file.write(f'    {formatted_chunk}')
        output_file.write(',\n' if i + chunk_size < num_bytes else '\n')

    # end array
    output_file.write('};\n')

    # write the size of the image in bytes
    output_file.write(f'const size_t img_size = {num_bytes};\n')
