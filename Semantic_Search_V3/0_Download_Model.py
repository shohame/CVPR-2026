from huggingface_hub import snapshot_download
import os

model_id = "Snowflake/snowflake-arctic-embed-l-v2.0"
local_directory = "./my_local_model"

# Create the directory if it doesn't exist
os.makedirs(local_directory, exist_ok=True)

print(f"Downloading {model_id} to {local_directory}...")

# Download the model files directly to the local directory
# We ignore some unnecessary files like weights in formats we don't need (e.g. .h5 or .msgpack)
# to save time and disk space.
snapshot_download(repo_id=model_id,
                local_dir=local_directory,
                ignore_patterns=["*.h5", "*.ot", "*.msgpack", "*.rust_model"],
                # local_dir_use_symlinks=False is generally recommended to avoid symlink confusion on some OS
                local_dir_use_symlinks=False
            )

print("Download complete!")