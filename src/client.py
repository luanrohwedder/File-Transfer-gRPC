from tkinter import filedialog, messagebox, ttk
import protos.file_transfer_pb2 as ft
import protos.file_transfer_pb2_grpc as ft_grpc

import tkinter as tk
import argparse
import grpc
import os

class FileTransferClient:
    def __init__(self, port):
        self.channel = grpc.insecure_channel(f'localhost:{port}')
        self.stub = ft_grpc.FileTransferStub(self.channel)
        
    def upload_file(self, filepath):
        filename = os.path.splitext(os.path.basename(filepath))[0]
        extension = os.path.splitext(os.path.basename(filepath))[1][1:]
        size = os.path.getsize(filepath)

        def file_chunks(): 
            metadata = ft.MetaData(filename=filename, extension=extension, size=size)
            yield ft.UploadFileRequest(metadata=metadata)

            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(1024 * 1024)
                    if not chunk:
                        break
                    yield ft.UploadFileRequest(
                        chunk=ft.FileChunk(content=chunk)
                    )
                    
        response = self.stub.UploadFile(file_chunks())
        return response
    
    def download_file(self, filename, extension, save_path):
        request = ft.FileRequest(filename=filename, extension=extension)
        response_stream = self.stub.DownloadFile(request)
        
        with open(save_path, "wb") as f:
            for chunk in response_stream:
                f.write(chunk.content)
    
    def delete_file(self, filename, extension):
        request = ft.FileRequest(filename=filename, extension=extension)
        response = self.stub.DeleteFile(request)
        
        return response
        
    def list_files(self):
        response = self.stub.ListFiles(ft.Empty())
        return response.files
    
    def drive_space(self):
        response = self.stub.DriveSpace(ft.Empty())
        return response.total_space, response.used_space
    
class App:
    def __init__(self, root: tk.Tk, client: FileTransferClient):
        self.client = client
        self.root = root

        self.init_frame()
        self.list_files()
        self.drive_space()
    
    def init_frame(self):
        bt_width = 20
        
        self.root.title("File Trasnfer Client")
        self.root.geometry("896x504")
        self.root.resizable(True, True)
                
        self.upload_button = ttk.Button(self.root, text="Upload File", command=self.upload_file, width=bt_width)
        self.upload_button.grid(row=0, column=0, padx=5, pady=10)
        
        self.download_button = ttk.Button(self.root, text="Download File", command=self.download_file, width=bt_width)
        self.download_button.grid(row=0, column=1, padx=5, pady=10)
        
        self.download_button = ttk.Button(self.root, text="Delete File", command=self.delete_file, width=bt_width)
        self.download_button.grid(row=0, column=2, padx=5, pady=10)
        
        self.update_button = tk.Button(self.root, text="Update", command=self.list_files, width=bt_width)
        self.update_button.grid(row=0, column=3, padx=5, pady=10)

        self.drive_info_label = ttk.Label(self.root, text="")
        self.drive_info_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        self.drive_space_progressbar = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=200, mode='determinate')
        self.drive_space_progressbar.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        self.tree = ttk.Treeview(self.root, columns=("Name", "Size"), show="headings")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Size", text="Size")
        self.tree.column("Size", anchor="center", width=1)
        self.tree.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
        
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_columnconfigure(2, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
       
    def upload_file(self):
        filepath = filedialog.askopenfilename()
        
        if filepath:
            response = self.client.upload_file(filepath)

            if response.success:
                messagebox.showinfo("Success", response.message)
                self.list_files()
                self.drive_space()
            else:
                messagebox.showinfo("Error", response.message)
                
    def download_file(self):
        selected = self.tree.focus()
        
        if selected:
            item = self.tree.item(selected)
            values = item.get("values", [])
            
            if values:
                filename_extension = values[0]
                filename = os.path.splitext(filename_extension)[0]
                extension = os.path.splitext(filename_extension)[1][1:]
                save_path = filedialog.asksaveasfilename(initialfile=filename)

                if save_path:
                    try:
                        save_path_extension = f'{save_path}.{extension}'
                        self.client.download_file(filename, extension, save_path_extension)
                        messagebox.showinfo("Success", f'File {filename} downloaded successfully')
                    except grpc.RpcError as e:
                        messagebox.showerror("Error", f"Failed to download file: {e.details()}")
    
    def delete_file(self):
        selected = self.tree.focus()
        
        if selected:
            item = self.tree.item(selected)
            values = item.get("values", [])
            
            if values:
                filename_extension = values[0]
                filename = os.path.splitext(filename_extension)[0]
                extension = os.path.splitext(filename_extension)[1][1:]
                confirm = messagebox.askyesno("Confirmation", f"Do you really want to delete the file: {filename_extension}?")
                
                if confirm:
                    response = self.client.delete_file(filename, extension)
                       
                    if response.success:
                        messagebox.showinfo("Success", response.message)
                        self.list_files()
                        self.drive_space
                    else:
                        messagebox.showinfo("Error", response.message)        

    def list_files(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        files = self.client.list_files()
        
        for file in files:
            filename = file.filename
            size = file.size
            self.tree.insert("", "end", values=(filename, self.format_size(size)))
            
        self.drive_space()
            
    def drive_space(self):
        total_space, used_space = self.client.drive_space()
        space_percentage = (used_space / total_space) * 100
        
        self.drive_space_progressbar["value"] = space_percentage
        self.drive_info_label["text"] = f"Drive Space: {self.format_size(total_space)} / Used: {self.format_size(used_space)}"
            
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-port', type=str, required=True, help='port')
    args = parser.parse_args()
    
    client = FileTransferClient(args.port)
    root = tk.Tk()
    app = App(root, client)
    root.mainloop()