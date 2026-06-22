import os
import cv2
import shutil
import random
from pathlib import Path

# Your dataset class mapping — derived from folder names
# This is what satisfies the "policy-grounded" requirement
CLASS_MAP = {
    "0_safe_walkway_violation":          {"id": 0, "name": "Safe Walkway Violation",          "policy_section": "Section 3.3.2", "severity": "CRITICAL"},
    "1_unauthorized_intervention":       {"id": 1, "name": "Unauthorized Intervention",        "policy_section": "Section 4.3.2", "severity": "HIGH"},
    "2_opened_panel_cover":              {"id": 2, "name": "Opened Panel Cover",               "policy_section": "Section 5.2.2", "severity": "LOW"},
    "3_carrying_overload_with_forklift": {"id": 3, "name": "Carrying Overload with Forklift", "policy_section": "Section 6.3.2", "severity": "CRITICAL"},
    "4_safe_walkway":                    {"id": 4, "name": "Safe Walkway",                     "policy_section": "Section 3.3.1", "severity": None},
    "5_authorized_intervention":         {"id": 5, "name": "Authorized Intervention",          "policy_section": "Section 4.3.1", "severity": None},
    "6_closed_panel_cover":              {"id": 6, "name": "Closed Panel Cover",               "policy_section": "Section 5.2.1", "severity": None},
    "7_safe_carrying":                   {"id": 7, "name": "Safe Carrying",                    "policy_section": "Section 6.3.1", "severity": None},
}

# Which classes are UNSAFE (will trigger alerts)
UNSAFE_CLASSES = {0, 1, 2, 3}

def extract_frames_from_videos(data_root="data/", output_dir="data/frames/", frames_per_video=10):
    """
    Go through every video in every class folder.
    Extract N evenly spaced frames from each video.
    Save frames as images with the class label in the filename.
    
    Why frames_per_video=10?
    Videos are 3-18 seconds. 10 frames captures the behavior 
    without creating millions of images that slow training.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    total_frames = 0
    class_counts = {}
    
    # Go through train and test folders
    for split in ["train", "test"]:
        split_path = os.path.join(data_root, split)
        if not os.path.exists(split_path):
            continue
            
        # Go through each class folder
        for folder_name, class_info in CLASS_MAP.items():
            folder_path = os.path.join(split_path, folder_name)
            if not os.path.exists(folder_path):
                print(f"Warning: {folder_path} not found, skipping")
                continue
            
            class_id = class_info["id"]
            out_class_dir = os.path.join(output_dir, split, str(class_id))
            os.makedirs(out_class_dir, exist_ok=True)
            
            # Process each video file in this folder
            video_files = [f for f in os.listdir(folder_path) 
                          if f.endswith(('.mp4', '.avi', '.mov', '.MP4'))]
            
            for video_file in video_files:
                video_path = os.path.join(folder_path, video_file)
                cap = cv2.VideoCapture(video_path)
                
                total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if total_video_frames == 0:
                    cap.release()
                    continue
                
                # Pick N evenly spaced frame indices
                # e.g. for a 90-frame video with frames_per_video=10:
                # indices = [0, 10, 20, 30, 40, 50, 60, 70, 80, 89]
                indices = [int(i * total_video_frames / frames_per_video) 
                          for i in range(frames_per_video)]
                
                video_name = Path(video_file).stem  # filename without extension
                
                for idx in indices:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    ret, frame = cap.read()
                    if not ret:
                        continue
                    
                    # Save frame as JPEG
                    # Naming: videoname_frameindex.jpg
                    frame_filename = f"{video_name}_frame{idx}.jpg"
                    frame_path = os.path.join(out_class_dir, frame_filename)
                    cv2.imwrite(frame_path, frame)
                    total_frames += 1
                
                cap.release()
            
            count = len(os.listdir(out_class_dir))
            class_counts[class_info["name"]] = count
            print(f"  [{class_id}] {class_info['name']}: {count} frames extracted")
    
    print(f"\nTotal frames extracted: {total_frames}")
    print("Saved to:", output_dir)
    return class_counts

if __name__ == "__main__":
    print("Extracting frames from all videos...")
    extract_frames_from_videos()