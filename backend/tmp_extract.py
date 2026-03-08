import json
import random

def main():
    with open("data/map.json", encoding="utf-8") as f:
        d = json.load(f)
    
    nodes = d["nodes"]
    random.seed(42)
    sampled_ambs = random.sample(nodes, 10)
    sampled_hosps = random.sample(nodes, 2)
    
    with open("tmp_out.txt", "w", encoding="utf-8") as out:
        out.write("---AMBs---\n")
        for i, n in enumerate(sampled_ambs, 6):
            out.write(f'    ("AMB-{i:02d}", "Unit {i:02d}", "{n["id"]}"),  # {n["label"]}\n')
            
        out.write("---HOSPs---\n")
        var = 4
        for n in sampled_hosps:
            out.write(f'    ("H-{var:02d}", "Hospital {var:02d}", "{n["id"]}", {random.randint(100, 500)}, {random.randint(50, 450)}),  # {n["label"]}\n')
            var += 1

if __name__ == "__main__":
    main()
