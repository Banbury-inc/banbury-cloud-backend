import requests
import json

def test_ping():
    response = requests.get('http://0.0.0.0:8082/ping/')
    data = response.json()
    print(data)

def test_run_pipeline():
    response = requests.get('http://0.0.0.0:8082/run_pipeline/mmills/')
    data = response.json()
    print(data)



def main():
    test_ping()
    test_run_pipeline()

if __name__ == '__main__':
    main()
