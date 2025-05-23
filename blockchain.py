import requests
from web3 import Web3



def debug_infura_connection():
    url = "https://sepolia.infura.io/v3/43f27092d24c4dfba5e41e010e634750"

    print("\n--- 1. Testing Raw Requests ---")
    try:
        # 确保请求头和内容与 web3.py 可能发送的相似
        response = requests.post(
            url,
            json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
            headers={"Content-Type": "application/json", "Accept": "application/json"}
        )
        print(f"[1] Raw Request Status Code: {response.status_code}")
        print(f"[1] Response Content: {response.text}")
        if response.status_code != 200:
            print(f"[1] WARNING: Raw request failed with status code {response.status_code}. Check Infura status or API key.")
            return False
    except Exception as e:
        print(f"[1] Raw Request Failed: {type(e).__name__}: {e}")
        return False

    print("\n--- 2. Testing Web3 Connection ---")
    try:
        # 启用 web3 的内部日志，可能会提供更多线索
        # 如果你有代理，也在这里设置
        # w3 = Web3(Web3.HTTPProvider(url, request_kwargs={'proxies': {'http': 'http://your.proxy:port', 'https': 'https://your.proxy:port'}}))
        w3 = Web3(Web3.HTTPProvider(url))
        print(f"[2] Web3 Connected Status: {w3.is_connected()}")
        if w3.is_connected():
            print(f"[2] Latest Block Number: {w3.eth.block_number}")
        else:
            print("[2] Web3 connection failed. Check logs for details.")
            return False
        return True
    except requests.exceptions.ConnectionError as ce:
        print(f"[2] Web3 Connection Error (requests.exceptions.ConnectionError): {ce}")
        print("This usually means a network issue or the server refused the connection.")
        return False
    except Exception as e:
        print(f"[2] Web3 Connection Exception: {type(e).__name__}: {e}")
        print("An unexpected error occurred during Web3 connection.")
        return False

if __name__ == "__main__":
    debug_infura_connection()