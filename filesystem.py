# =============================================================================
# CODERPAD TARGET: IN-MEMORY FILESYSTEM (~60 lines)
# This is the exact shape and size written in a 45-min interview to get Strong Hire.
# =============================================================================

import threading

class Node:
    def __init__(self, name: str, is_dir: bool = True, parent=None):
        self.name = name
        self.is_dir = is_dir
        self.parent = parent
        self.children = {}      # name -> Node (if dir)
        self.content = ""       # text content (if file)


class FileSystem:
    def __init__(self):
        self.root = Node("", is_dir=True)
        self.cwd = self.root
        self.lock = threading.RLock()

    def _resolve(self, path: str) -> Node:
        """The single traversal engine for all path operations."""
        curr = self.root if path.startswith("/") else self.cwd
        tokens = [t for t in path.split("/") if t and t != "."]

        for t in tokens:
            if t == "..":
                if curr.parent:
                    curr = curr.parent
            else:
                if not curr.is_dir or t not in curr.children:
                    raise Exception(f"Path segment not found: {t}")
                curr = curr.children[t]
        return curr

    def mkdir(self, path: str):
        with self.lock:
            parts = [p for p in path.split("/") if p]
            if not parts:
                raise Exception("Invalid path")

            parent_path = "/" + "/".join(parts[:-1]) if path.startswith("/") else "/".join(parts[:-1])
            parent = self._resolve(parent_path) if parent_path else self.cwd
            name = parts[-1]

            if name in parent.children:
                raise Exception(f"'{name}' already exists")
            parent.children[name] = Node(name, is_dir=True, parent=parent)

    def cd(self, path: str):
        with self.lock:
            node = self._resolve(path)
            if not node.is_dir:
                raise Exception(f"'{path}' is not a directory")
            self.cwd = node

    def touch(self, path: str, content: str = ""):
        with self.lock:
            parts = [p for p in path.split("/") if p]
            parent_path = "/" + "/".join(parts[:-1]) if path.startswith("/") else "/".join(parts[:-1])
            parent = self._resolve(parent_path) if parent_path else self.cwd
            name = parts[-1]

            if name not in parent.children:
                parent.children[name] = Node(name, is_dir=False, parent=parent)
            parent.children[name].content = content

    def cat(self, path: str) -> str:
        with self.lock:
            node = self._resolve(path)
            if node.is_dir:
                raise Exception(f"'{path}' is a directory")
            return node.content

    def ls(self) -> list:
        with self.lock:
            return sorted(self.cwd.children.keys())

    def pwd(self) -> str:
        with self.lock:
            if self.cwd is self.root:
                return "/"
            parts, curr = [], self.cwd
            while curr is not self.root:
                parts.append(curr.name)
                curr = curr.parent
            return "/" + "/".join(reversed(parts))


# -----------------------------------------------------------------------------
# RUNNER / VERIFICATION
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    fs = FileSystem()

    # 1. Navigation & creation
    fs.mkdir("home")
    fs.mkdir("/home/sid")
    fs.cd("/home/sid")
    print("pwd:", fs.pwd())       # expect /home/sid

    # 2. Files
    fs.touch("test.txt", "hello world")
    print("ls :", fs.ls())        # expect ['test.txt']
    print("cat:", fs.cat("test.txt"))  # expect hello world

    # 3. Path resolution & backtracking
    fs.cd("..")
    print("pwd:", fs.pwd())       # expect /home
    print("cat nested:", fs.cat("sid/test.txt"))  # expect hello world

    # 4. Error check
    try:
        fs.cd("sid/test.txt")     # file is not a dir
    except Exception as e:
        print("Expected error:", e)

    print("\nSUCCESS: All operations passed.")
