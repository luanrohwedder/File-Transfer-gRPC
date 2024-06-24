from concurrent import futures
from protos import file_transfer_pb2
from protos import file_transfer_pb2_grpc

import os
import argparse
import grpc

total_space = 1000000

def calculate_used_space(dir):
    total = 0
    
    for root, dirs, files in os.walk(dir):
        for filename in files:
            filepath = os.path.join(root, filename)
            total += os.path.getsize(filepath)
            
    return total

def calculate_space(size, dir):
    used = calculate_used_space(dir)
    total = used + size
    
    if total_space > total:
        return False
    else:
        return True

class FileTrasnferServicer(file_transfer_pb2_grpc.FileTransferServicer):
    def __init__(self):
        self.storage_dir = "server_storage"
        os.makedirs(self.storage_dir, exist_ok=True)
        
    def UploadFile(self, request_iterator, context):
        filename = None
        filepath = None
        data = bytearray()
        
        for request in request_iterator:
            if request.HasField('metadata'):
                size = request.metadata.size
                no_space = calculate_space(size, self.storage_dir)
                
                if no_space:
                    return file_transfer_pb2.Status(success=False, message="No space available for upload")
                
                filename = f'{request.metadata.filename}.{request.metadata.extension}'
                filepath = os.path.join(self.storage_dir, filename)
            elif request.HasField('chunk'):
                data.extend(request.chunk.content)
        
        if filepath is None:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details('No file metadata provided')
            return file_transfer_pb2.Status(success=False, message="Failed to upload file")        
    
        with open(filepath, "wb") as f:
            f.write(data)
            
        return file_transfer_pb2.Status(success=True, message="File upload successfully!")
    
    def DownloadFile(self, request, context):
        filename = f'{request.filename}.{request.extension}'
        filepath = os.path.join(self.storage_dir, filename)

        if os.path.exists(filepath):
            try:
                with open(filepath, "rb") as f:
                    while True:
                        chunk = f.read(1024 * 1024)
                        if chunk:
                            yield file_transfer_pb2.FileChunk(content=chunk)
                        else:
                            break
            except Exception as e:
                context.set_details(f'Error reading file: {e}')
                context.set_code(grpc.StatusCode.INTERNAL)
        else:
            context.set_details("File not found")
            context.set_code(grpc.StatusCode.NOT_FOUND)

    def DeleteFile(self, request, context):
        filename = f'{request.filename}.{request.extension}'
        filepath = os.path.join(self.storage_dir, filename)
        
        if (os.path.exists(filepath)):
            try:
                os.remove(filepath)
                return file_transfer_pb2.Status(success=True, message="File deleted successfully!")
            except Exception as e:
                context.set_details(f'Error deleting file: {e}')
                context.set_code(grpc.StatusCode.INTERNAL)
                return file_transfer_pb2.Status(success=False, message="Error deleting selected file!")
        else:
            context.set_details("File not found")
            context.set_code(grpc.StatusCode.NOT_FOUND)
            
    def ListFiles(self, request, context):
        files = []
        
        for filename in os.listdir(self.storage_dir):
            filepath = os.path.join(self.storage_dir, filename)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath)
                files.append(file_transfer_pb2.FileInfo(filename=filename, size=size))
        
        return file_transfer_pb2.FileList(files=files)
    
    def DriveSpace(self, request, context):
        used_space = calculate_used_space(self.storage_dir)
        return file_transfer_pb2.Space(total_space=total_space, used_space=used_space)
        
    
def server(port):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    file_transfer_pb2_grpc.add_FileTransferServicer_to_server(FileTrasnferServicer(), server)
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f'Server running on port: {port}')
    server.wait_for_termination()
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-port', type=str, required=True, help='port')
    args = parser.parse_args()
    
    server(args.port)