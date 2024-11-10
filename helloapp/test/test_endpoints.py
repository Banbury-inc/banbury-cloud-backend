import requests
import json

def test_ping():
    response = requests.get('http://0.0.0.0:8082/ping/')
    data = response.json()
    print(data)





def main():
    test_ping()

if __name__ == '__main__':
    main()
