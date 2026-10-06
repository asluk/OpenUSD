"""Execute the pinned proposal candidate; historical experiments are in Git history."""
from pathlib import Path
import argparse
from candidate.runner import execute

def main():
    p=argparse.ArgumentParser()
    for name in ['grids','usd-sdk','native-build','native-proj','native-python','ov-sdk','python-dependencies','output','cmake']:
        p.add_argument('--'+name,required=True)
    args=p.parse_args()
    execute(Path(__file__).resolve().parent,args)

if __name__=='__main__':main()
