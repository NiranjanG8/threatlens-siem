def parse_logs(file_path):
    with open(file_path, "r") as f:
        return [line.strip() for line in f]
