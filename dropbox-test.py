import dropbox
from dropbox.files import FileMetadata, FolderMetadata

# Replace with your access token
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

def read_dropbox_token():
    """Read Dropbox auth token from a file."""
    file_path="./dropbox_token.txt"
    try:
        with open(file_path, "r") as f:
            token = f.read().strip()
        return token
    except FileNotFoundError:
        raise RuntimeError(f"Token file not found: {file_path}")
    except Exception as e:
        raise RuntimeError(f"Error reading token: {e}")
        
def list_folders(path, list_folders_only=True):

    dropbox_token = read_dropbox_token()
    dbx = dropbox.Dropbox(dropbox_token)

    try:
        result = dbx.files_list_folder(path)

        entries = []
        for e in result.entries:
            if isinstance(e, FolderMetadata):
                entries.append(("folder", e.name, e.path_lower))
            elif not list_folders_only and isinstance(e, FileMetadata):
                entries.append(("file", e.name, e.path_lower))

        # folders = []
        # for entry in result.entries:
        #     if isinstance(entry, FolderMetadata):
        #         folders.append(entry.name)

        # Handle pagination (if many items)
        while result.has_more:
            result = dbx.files_list_folder_continue(result.cursor)
            for e in result.entries:
                if isinstance(e, FolderMetadata):
                    entries.append(("folder", e.name, e.path_lower))
                elif not list_folders_only and isinstance(e, FileMetadata):
                    entries.append(("file", e.name, e.path_lower))

        return entries

    except Exception as e:
        print(f"Error: {e}")
        return []


if __name__ == "__main__":
    # "" = root directory, or use "/your/folder"
    folder_path = "/motion_images"

    folders = list_folders(folder_path, False)

    print("Folders:")
    for f in folders:
        print(f"- {f}")
        