import os
import torch
import time
from ultralytics import YOLO

if torch.cuda.is_available():
    torch.cuda.empty_cache()

start_epoch_time = 0
first_epoch_done = False

def on_epoch_start(trainer):
    global start_epoch_time
    start_epoch_time = time.time()

def on_epoch_end(trainer):
    global start_epoch_time, first_epoch_done
    if not first_epoch_done:
        first_epoch_done = True
        end_time = time.time()
        time_taken = end_time - start_epoch_time
        gpu_mem = torch.cuda.memory_reserved(0) / 1024**3 if torch.cuda.is_available() else 0
        
        print("\n==================================================")
        print(f"RESUMED FROM EPOCH: 3")
        print(f"CURRENT EPOCH: {trainer.epoch + 1}")
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"BATCH: {trainer.args.batch}")
        print(f"IMAGE SIZE: {trainer.args.imgsz}")
        print(f"GPU MEMORY: {gpu_mem:.2f} GB")
        print(f"TIME FOR RESUMED EPOCH: {time_taken:.2f} seconds")
        print(f"CPU PREVIOUS TIME/EPOCH: ~315 seconds")
        if time_taken > 0:
            print(f"SPEEDUP: {315 / time_taken:.2f}x")
        print("==================================================\n")

def try_resume():
    model = YOLO("runs/detect/runs/detect/person_v2/weights/last.pt")
    model.add_callback("on_train_epoch_start", on_epoch_start)
    model.add_callback("on_train_epoch_end", on_epoch_end)
    
    # We pass the overrides requested by user
    train_args = {
        "resume": True,
        "device": 0,
        "workers": 4,
        "amp": True,
        "imgsz": 640
    }
    
    print(f"Attempting resume with args: {train_args}")
    model.train(**train_args)

if __name__ == "__main__":
    try:
        try_resume()
    except Exception as e:
        err_str = str(e)
        if "CUDA out of memory" in err_str or "CUDA error: out of memory" in err_str:
            print("\n[WARNING] CUDA OOM with original batch size. Updating args.yaml to batch=4...")
            torch.cuda.empty_cache()
            
            # Manually update args.yaml because Ultralytics `resume=True` heavily relies on it
            import yaml
            args_path = "runs/detect/runs/detect/person_v2/args.yaml"
            with open(args_path, "r") as f:
                args = yaml.safe_load(f)
            args["batch"] = 4
            with open(args_path, "w") as f:
                yaml.dump(args, f)
            
            try:
                try_resume()
            except Exception as e2:
                err_str2 = str(e2)
                if "CUDA out of memory" in err_str2 or "CUDA error: out of memory" in err_str2:
                    print("\n[WARNING] CUDA OOM with batch=4. Updating args.yaml to batch=2...")
                    torch.cuda.empty_cache()
                    
                    with open(args_path, "r") as f:
                        args = yaml.safe_load(f)
                    args["batch"] = 2
                    with open(args_path, "w") as f:
                        yaml.dump(args, f)
                    
                    try_resume()
                else:
                    raise e2
        else:
            raise e
