from bitcoinrpc.authproxy import AuthServiceProxy

RPC_URL = "http://alice:password@127.0.0.1:18443"


def rpc(wallet=None):
    return AuthServiceProxy(f"{RPC_URL}/wallet/{wallet}") if wallet else AuthServiceProxy(RPC_URL)


def ensure_wallet(client, wallets, name):
    """Create or load a wallet if not already loaded."""
    if name in wallets:
        return
    try:
        client.createwallet(name)
    except Exception:
        # Wallet already exists on disk, load it
        try:
            client.loadwallet(name)
        except Exception as e:
            print(f"Failed to load wallet {name}: {e}")
            raise


def main():
    # Connect to the node (no wallet)
    client = rpc()

    # List currently loaded wallets
    wallets = client.listwallets()

    # Ensure both wallets exist and are loaded
    ensure_wallet(client, wallets, "Miner")
    ensure_wallet(client, wallets, "Trader")

    # Get wallet-specific RPC connections
    miner = rpc("Miner")
    trader = rpc("Trader")

    # ----------------------------
    # Mining setup (ONLY ONCE)
    # ----------------------------
    mining_address = miner.getnewaddress("Mining Reward", "bech32")
    # Generate 101 blocks to make the coinbase spendable
    miner.generatetoaddress(101, mining_address)

    balance = miner.getbalance()
    print(f"Balance after mining: {balance}")

    # ----------------------------
    # Trader address
    # ----------------------------
    trader_address = trader.getnewaddress("Received", "bech32")

    # ----------------------------
    # Send transaction
    # ----------------------------
    txid = miner.sendtoaddress(trader_address, 20)

    # ----------------------------
    # Confirm transaction
    # ----------------------------
    miner.generatetoaddress(1, mining_address)

    # ----------------------------
    # Transaction details
    # ----------------------------
    tx = client.getrawtransaction(txid, True)

    vin = tx["vin"][0]
    prev_tx = client.getrawtransaction(vin["txid"], True)
    prev_out = prev_tx["vout"][vin["vout"]]

    miner_input_address = prev_out["scriptPubKey"]["address"]
    miner_input_amount = prev_out["value"]

    trader_output_amount = None
    change_address = None
    change_amount = 0.0

    for vout in tx["vout"]:
        addr = vout["scriptPubKey"]["address"]
        value = vout["value"]
        if addr == trader_address:
            trader_output_amount = value
        else:
            change_address = addr
            change_amount = value

    # If there is no change output, treat it as 0
    if change_address is None:
        change_address = "N/A"
        change_amount = 0.0

    fee = miner_input_amount - trader_output_amount - change_amount

    blockhash = tx["blockhash"]
    block = client.getblock(blockhash)
    height = block["height"]

    # ----------------------------
    # Write output
    # ----------------------------
    with open("out.txt", "w") as f:
        f.write(f"{txid}\n")
        f.write(f"{miner_input_address}\n")
        f.write(f"{miner_input_amount}\n")
        f.write(f"{trader_address}\n")
        f.write(f"{trader_output_amount}\n")
        f.write(f"{change_address}\n")
        f.write(f"{change_amount}\n")
        f.write(f"{fee}\n")
        f.write(f"{height}\n")
        f.write(f"{blockhash}\n")

    print("Done. Output written to out.txt")


if __name__ == "__main__":
    main()